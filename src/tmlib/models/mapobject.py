import json
import os
import logging
import random
import collections

import pandas as pd
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from geoalchemy2.functions import GenericFunction
from sqlalchemy.orm import Session
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, not_
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import UniqueConstraint

from tmlib.models.base import Model, DateMixIn
from tmlib.utils import autocreate_directory_property

logger = logging.getLogger(__name__)


class ST_ExteriorRing(GenericFunction):
    name = 'ST_ExteriorRing'
    type = Geometry


class MapobjectType(Model, DateMixIn):

    '''A *map object type* represent a conceptual group of *map objects*
    (segmented objects) that reflect different biological entities,
    such as "cells" or "nuclei" for example.

    Attributes
    ----------
    name: str
        name of the map objects type
    max_poly_zoom: int
        zoom level where mapobjects are no longer visualized
    min_poly_zoom: int
        zoom level where visualization should switch from centroids
        to outlines
    experiment_id: int
        ID of the parent experiment
    experiment: tmlib.models.Experiment
        parent experiment to which map objects belong
    mapobjects: List[tmlib.models.Mapobject]
        mapobjects that belong to the mapobject type
    '''

    #: str: name of the corresponding database table
    __tablename__ = 'mapobject_types'

    __table_args__ = (UniqueConstraint('name', 'experiment_id'), )

    # Table columns
    name = Column(String, index=True, nullable=False)
    is_static = Column(Boolean, index=True)
    _max_poly_zoom = Column('max_poly_zoom', Integer)
    _min_poly_zoom = Column('min_poly_zoom', Integer)
    experiment_id = Column(
        Integer,
        ForeignKey('experiments.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    #: Relationship to other tables
    experiment = relationship(
        'Experiment',
        backref=backref('mapobject_types', cascade='all, delete-orphan')
    )

    def __init__(self, name, experiment_id, is_static=False):
        '''
        Parameters
        ----------
        name: str
            name of the map objects type, e.g. "cells"
        experiment_id: int
            ID of the parent experiment
        static: bool, optional
            whether map objects outlines are fixed across different time
            points and z-planes (default: ``False``)
        '''
        self.name = name
        self.experiment_id = experiment_id
        self.is_static = is_static

    @autocreate_directory_property
    def location(self):
        '''str: location where data related to the mapobject type is stored'''
        return os.path.join(self.experiment.mapobject_types_location, self.name)

    @hybrid_property
    def min_poly_zoom(self):
        '''int: zoom level at which visualization switches from drawing
        polygons instead of centroids
        '''
        return self._min_poly_zoom

    @min_poly_zoom.setter
    def min_poly_zoom(self, value):
        self._min_poly_zoom = value

    @hybrid_property
    def max_poly_zoom(self):
        '''int: zoom level at which mapobjects are no longer visualized
        '''
        return self._max_poly_zoom

    @max_poly_zoom.setter
    def max_poly_zoom(self, value):
        self._max_poly_zoom = value

    def get_mapobject_outlines_within_tile(self, x, y, z, tpoint, zplane):
        '''Get outlines of all objects that fall within a given pyramid tile,
        defined by their `y`, `x`, `z` coordinates.

        Parameters
        ----------
        session: sqlalchemy.orm.session.Session
            database session
        x: int
            column map coordinate at the given `z` level
        y: int
            row map coordinate at the given `z` level
        z: int
            zoom level
        tpoint: int
            time point index
        zplane: int
            z-plane index

        Returns
        -------
        List[Tuple[int, str]]
            GeoJSON string for each selected map object

        Note
        ----
        If `z` > `min_poly_zoom` mapobjects are represented by polygons.
        If `min_poly_zoom` > `z` > `max_poly_zoom`, mapobjects are represented
        by points and if `z` < `max_poly_zoom` they are not displayed at all.
        '''

        maxzoom = self.experiment.channels[0].layers[0].maxzoom_level_index

        session = Session.object_session(self)

        do_simplify = self.max_poly_zoom <= z < self.min_poly_zoom
        do_nothing = z < self.max_poly_zoom
        if do_simplify:
            select_stmt = session.query(
                MapobjectOutline.mapobject_id,
                MapobjectOutline.geom_centroid.ST_AsGeoJSON())
        elif do_nothing:
            return list()
        else:
            select_stmt = session.query(
                MapobjectOutline.mapobject_id,
                MapobjectOutline.geom_poly.ST_AsGeoJSON())

        outlines = select_stmt.\
            join(MapobjectOutline.mapobject).\
            join(MapobjectType).\
            filter(
                (MapobjectType.id == self.id) &
                ((MapobjectType.is_static) |
                 (MapobjectOutline.tpoint == tpoint) &
                 (MapobjectOutline.zplane == zplane)) &
                (MapobjectOutline.intersection_filter(x, y, z, maxzoom))
            ).\
            all()

        return outlines

    def calculate_min_max_poly_zoom(self, maxzoom_level, mapobject_outline_ids,
                                n_sample=10, n_points_per_tile_limit=3000):
        '''Calculates the minimum zoom level above which mapobjects are
        represented on the map as polygons instead of centroids and the
        maximum zoom level below which mapobjects are no longer visualized.

        Parameters
        ----------
        maxzoom_level: int
            maximum zoom level of the pyramid
        mapobject_outline_ids: List[int]
            IDs of instances of :py:class:`tmlib.models.MapobjectOutline`
        n_sample: int, optional
            number of tiles that should be sampled (default: ``10``)
        n_points_per_tile_limit: int, optional
            maximum number of points per tile that are allowed before the
            polygon geometry is simplified to a point (default: ``3000``)

        Returns
        -------
        Tuple[int]
            minimal and maximal zoom level
        '''
        session = Session.object_session(self)

        n_points_in_tile_per_z = dict()
        for z in range(maxzoom_level, -1, -1):
            tilesize = 256 * 2 ** (6 - z)

            rand_xs = [random.randrange(0, 2**z) for _ in range(n_sample)]
            rand_ys = [random.randrange(0, 2**z) for _ in range(n_sample)]

            n_points_in_tile_samples = []
            for x, y in zip(rand_xs, rand_ys):
                x0 = x * tilesize
                y0 = -y * tilesize

                minx = x0
                maxx = x0 + tilesize
                miny = y0 - tilesize
                maxy = y0

                tile = (
                    'LINESTRING({maxx} {maxy},{minx} {maxy}, {minx} {miny}, '
                    '{maxx} {miny}, {maxx} {maxy})'.format(
                            minx=minx, maxx=maxx, miny=miny, maxy=maxy
                        )
                )

                n_points_in_tile = session.query(
                        func.sum(MapobjectOutline.geom_poly.ST_NPoints())
                    ).\
                    filter(
                        MapobjectOutline.id.in_(mapobject_outline_ids),
                        MapobjectOutline.geom_poly.intersects(tile)
                    ).\
                    scalar()

                if n_points_in_tile is not None:
                    n_points_in_tile_samples.append(n_points_in_tile)
                else:
                    n_points_in_tile_samples.append(0)

            n_points_in_tile_per_z[z] = int(
                float(sum(n_points_in_tile_samples)) /
                len(n_points_in_tile_samples)
            )

        min_poly_zoom = min([
            z for z, n in n_points_in_tile_per_z.items()
            if n <= n_points_per_tile_limit
        ])
        # TODO: calculate the optimal zoom level
        max_poly_zoom = 0
        return (min_poly_zoom, max_poly_zoom)

    def get_feature_value_matrix(self, feature_names): 
        '''Gets a wide format pandas data frame of feature values.

        Parameters
        ----------
        feature_names: List[str]
            names of features that will be used as labels of the data frame

        Returns
        -------
        pandas.DataFrame
            A data frame with features as columns and rows as mapobjects.
            The index of this data frame is set to the mapobject ids.
            As such the DF can be indexed using the syntax:
            feature_values_of_mapobject_x = df.loc[x]

        '''
        from tmlib.models import Feature, FeatureValue
        session = Session.object_session(self)
        feature_values = session.query(
            Feature.name, FeatureValue.mapobject_id, FeatureValue.value).\
            join(FeatureValue).\
            filter(
                (Feature.name.in_(set(feature_names))) &
                (Feature.mapobject_type_id == self.id)
            ).\
            all()
        feature_df_long = pd.DataFrame(feature_values)
        feature_df_long.columns = ['feature', 'mapobject', 'value']
        feature_df = pd.pivot_table(
            feature_df_long, values='value',
            index='mapobject', columns='feature'
        )
        return feature_df

    def __repr__(self):
        return '<MapobjectType(id=%d, name=%r)>' % (self.id, self.name)


class Mapobject(Model):

    '''A *map object* represents a connected pixel component in an
    image. It has outlines for drawing on the map and may also be associated
    with measurements (*features*), which can be queried or used for analysis.

    Attributes
    ----------
    mapobject_type_id: int
        ID of the parent mapobject
    mapobject_type: tmlib.models.MapobjectType
        parent mapobject type to which the mapobject belongs
    outlines: List[tmlib.models.MapobjectOutlines]
        outlines that belong to the mapobject
    feature_values: List[tmlib.models.FeatureValues]
        feature values that belong to the mapobject
    '''

    #: str: name of the corresponding database table
    __tablename__ = 'mapobjects'

    # Table columns
    mapobject_type_id = Column(
        Integer,
        ForeignKey('mapobject_types.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    # Relationships to other tables
    mapobject_type = relationship(
        'MapobjectType',
        backref=backref('mapobjects', cascade='all, delete-orphan')
    )

    def __init__(self, mapobject_type_id):
        '''
        Parameters
        ----------
        mapobject_type_id: int
            ID of the parent mapobject
        '''
        self.mapobject_type_id = mapobject_type_id

    def __repr__(self):
        return '<Mapobject(id=%d)>' % self.id


class MapobjectOutline(Model):

    '''Outline of an individual *map object*.

    Attributes
    ----------
    tpoint: int
        time point index
    zplane: int
        z-plane index
    geom_poly: str
        EWKT polygon geometry
    geom_centroid: str
        EWKT point geometry
    mapobject_id: int
        ID of parent mapobject
    mapobject: tmlib.models.Mapobject
        parent mapobject to which the outline belongs
    '''

    #: str: name of the corresponding database table
    __tablename__ = 'mapobject_outlines'

    # Table columns
    tpoint = Column(Integer, index=True)
    zplane = Column(Integer, index=True)
    geom_poly = Column(Geometry('POLYGON'), index=True)
    geom_centroid = Column(Geometry('POINT'), index=True)
    mapobject_id = Column(
        Integer,
        ForeignKey('mapobjects.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    # Relationships to other tables
    mapobject = relationship(
        'Mapobject',
        backref=backref('outlines', cascade='all, delete-orphan')
    )

    def __init__(self, mapobject_id, geom_poly=None, geom_centroid=None,
                 tpoint=None, zplane=None):
        '''
        Parameters
        ----------
        mapobject_id: int
            ID of parent mapobject
        tpoint: int, optional
            time point index (default: ``None``)
        zplane: int, optional
            z-plane index (default: ``None``)
        geom_poly: str, optional
            EWKT polygon geometry (default: ``None``)
        geom_centroid: str, optional
            EWKT point geometry (default: ``None``)
        '''
        self.tpoint = tpoint
        self.zplane = zplane
        self.mapobject_id = mapobject_id
        self.geom_poly = geom_poly
        self.geom_centroid = geom_centroid

    @staticmethod
    def create_tile(x, y, z, maxzoom):
        """Calculates the bounding box of a tile.

        Parameters
        ----------
        x: int
            horizontal tile coordiante
        y: int
            vertical tile coordiante
        z: int
            zoom level
        maxzoom: int
            maximal zoom level of layers belonging to the visualized experiment
        """
        # The extent of a tile of the current zoom level in mapobject
        # coordinates (i.e. coordinates on the highest zoom level)
        size = 256 * 2 ** (maxzoom - z)
        # Coordinates of the top-left corner of the tile
        x0 = x * size
        y0 = y * size
        # Coordinates with which to specify all corners of the tile
        minx = x0
        maxx = x0 + size
        miny = -y0 - size
        maxy = -y0
        return (minx, miny, maxx, maxy)

    @staticmethod
    def intersection_filter(x, y, z, maxzoom):
        '''Generates an `SQLalchemy` query filter to select mapobject outlines
        for a given `y`, `x`, `z` pyramid coordinate.

        Parameters
        ----------
        x: int
            column map coordinate at the given `z` level
        y: int
            row map coordinate at the given `z` level
        z: int
            zoom level
        maxzoom: int
            maximal zoom level of layers belonging to the visualized experiment

        Returns
        -------
        ???
        '''
        minx, miny, maxx, maxy = MapobjectOutline.create_tile(x, y, z, maxzoom)
        tile = 'POLYGON(({maxx} {maxy}, {minx} {maxy}, {minx} {miny}, {maxx} {miny}, {maxx} {maxy}))'.format(
            minx=minx, maxx=maxx, miny=miny, maxy=maxy)
        # The outlines should not lie on the top or left border since this
        # would otherwise lead to requests for neighboring tiles receiving
        # the same objects.
        # This in turn leads to overplotting and is noticeable when the objects
        # have a fill color with an opacity != 0 or != 1.
        top_border = 'LINESTRING({minx} {maxy}, {maxx} {maxy})'.format(
            minx=minx, maxx=maxx, maxy=maxy)
        left_border = 'LINESTRING({minx} {maxy}, {minx} {miny})'.format(
            minx=minx, maxy=maxy, miny=miny)

        spatial_filter = (MapobjectOutline.geom_poly.ST_Intersects(tile))
        if x != 0:
            spatial_filter = spatial_filter & \
                not_(ST_ExteriorRing(MapobjectOutline.geom_poly).\
                     ST_Intersects(left_border))
        if y != 0:
            spatial_filter = spatial_filter & \
                not_(ST_ExteriorRing(MapobjectOutline.geom_poly).\
                     ST_Intersects(top_border))

        return spatial_filter


class MapobjectSegmentation(Model):

    '''A *mapobject segmentation* associates a *mapobject outline* with the
    corresponding image acquisition *site* in which the object was identified.

    Attributes
    ----------
    pipeline: str
            name of the corresponding Jterator pipeline in which the objects
            were segmented
    is_border: bool
        whether the object touches at the border of a *site* and is
        therefore only partially represented on the corresponding image
    label: int
        one-based object identifier number which is unique per site
    tpoint: int, optional
        time point index (default: ``None``)
    zplane: int, optional
        z-plane index (default: ``None``)
    geom_poly: str, optional
        EWKT polygon geometry (default: ``None``)
    site_id: int
        ID of the parent site
    site: tmlib.models.Site
        site to which the segmentation belongs
    mapobject_id: int
        ID of the parent corresponding mapobject outline
    mapobject: tmlib.models.Mapobject
        mapobject to which the segmentation belongs
    '''

    #: str: name of the corresponding database table
    __tablename__ = 'mapobject_segmentations'

    __table_args__ = (
        UniqueConstraint('label', 'tpoint', 'zplane', 'site_id', 'mapobject_id'),
    )

    # Table columns
    is_border = Column(Boolean, index=True)
    label = Column(Integer, index=True)
    pipeline = Column(String, index=True)
    tpoint = Column(Integer, index=True)
    zplane = Column(Integer, index=True)
    geom_poly = Column(Geometry('POLYGON'))
    site_id = Column(
        Integer,
        ForeignKey('sites.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )
    mapobject_id = Column(
        Integer,
        ForeignKey('mapobjects.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    # Relationships to other tables
    site = relationship(
        'Site',
        backref=backref(
            'mapobject_segmentations', cascade='all, delete-orphan'
        )
    )
    mapobject= relationship(
        'Mapobject',
        backref=backref(
            'segmentation', cascade='all, delete-orphan', uselist=False
        )
    )

    def __init__(self, pipeline, label, tpoint, zplane, is_border, geom_poly,
            site_id, mapobject_id):
        '''
        Parameters
        ----------
        pipeline: str
            name of the corresponding Jterator pipeline in which the objects
            were segmented
        label: int
            one-based object identifier number which is unique per site
        tpoint: int, optional
            time point index (default: ``None``)
        zplane: int, optional
            z-plane index (default: ``None``)
        is_border: bool
            whether the object touches at the border of a *site* and is
            therefore only partially represented on the corresponding image
        geom_poly: str, optional
            EWKT polygon geometry (default: ``None``)
        site_id: int
            ID of the parent site
        mapobject_id: int
            ID of the parent corresponding mapobject
        '''
        self.pipeline = pipeline
        self.label = label
        self.tpoint = tpoint
        self.zplane = zplane
        self.geom_poly = geom_poly
        self.site_id = site_id
        self.mapobject_id = mapobject_id
        self.is_border = is_border

    # TODO: allow segmentations with point geometry as an alternative to
    # polygons (may be useful for small objects)

    def __repr__(self):
        return (
            '<MapobjectSegmentation('
                'id=%d, tlabel=%r, tpoint=%r, zplane=%r, site_id=%r, mapobject_id=%r'
            ')>'
            % (self.id, self.label, self.tpoint, self.zplane, self.site_id, self.mapobject_id)
        )
