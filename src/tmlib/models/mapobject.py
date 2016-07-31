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

from tmlib.models.base import ExperimentModel, DateMixIn
from tmlib.utils import autocreate_directory_property

logger = logging.getLogger(__name__)


class ST_ExteriorRing(GenericFunction):
    name = 'ST_ExteriorRing'
    type = Geometry


class MapobjectType(ExperimentModel, DateMixIn):

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
    mapobjects: List[tmlib.models.Mapobject]
        mapobjects that belong to the mapobject type
    '''

    #: str: name of the corresponding database table
    __tablename__ = 'mapobject_types'

    __table_args__ = (UniqueConstraint('name'), )

    # Table columns
    name = Column(String, index=True, nullable=False)
    is_static = Column(Boolean, index=True)
    _max_poly_zoom = Column('max_poly_zoom', Integer)
    _min_poly_zoom = Column('min_poly_zoom', Integer)

    def __init__(self, name, is_static=False, parent_id=None):
        '''
        Parameters
        ----------
        name: str
            name of the map objects type, e.g. "cells"
        static: bool, optional
            whether map objects outlines are fixed across different time
            points and z-planes (default: ``False``)
        '''
        self.name = name
        self.is_static = is_static

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
                MapobjectSegmentation.mapobject_id,
                MapobjectSegmentation.geom_centroid.ST_AsGeoJSON())
        elif do_nothing:
            return list()
        else:
            select_stmt = session.query(
                MapobjectSegmentation.mapobject_id,
                MapobjectSegmentation.geom_poly.ST_AsGeoJSON()
            )

        outlines = select_stmt.\
            join(MapobjectSegmentation.mapobject).\
            join(MapobjectType).\
            filter(
                (MapobjectType.id == self.id) &
                ((MapobjectType.is_static) |
                 (MapobjectSegmentation.tpoint == tpoint) &
                 (MapobjectSegmentation.zplane == zplane)) &
                (MapobjectSegmentation.intersection_filter(x, y, z, maxzoom))
            ).\
            all()

        return outlines

    def calculate_min_max_poly_zoom(self, maxzoom_level, segmentation_ids,
                                n_sample=10, n_points_per_tile_limit=3000):
        '''Calculates the minimum zoom level above which mapobjects are
        represented on the map as polygons instead of centroids and the
        maximum zoom level below which mapobjects are no longer visualized.

        Parameters
        ----------
        maxzoom_level: int
            maximum zoom level of the pyramid
        segmentation_ids: List[int]
            IDs of instances of :py:class:`tmlib.models.MapobjectSegmentation`
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
        # session = Session.object_session(self)

        # n_points_in_tile_per_z = dict()
        # for z in range(maxzoom_level, -1, -1):
            # tilesize = 256 * 2 ** (6 - z)

            # rand_xs = [random.randrange(0, 2**z) for _ in range(n_sample)]
            # rand_ys = [random.randrange(0, 2**z) for _ in range(n_sample)]

            # n_points_in_tile_samples = []
            # for x, y in zip(rand_xs, rand_ys):
            #     x0 = x * tilesize
            #     y0 = -y * tilesize

            #     minx = x0
            #     maxx = x0 + tilesize
            #     miny = y0 - tilesize
            #     maxy = y0

            #     tile = (
            #         'LINESTRING({maxx} {maxy},{minx} {maxy}, {minx} {miny}, '
            #         '{maxx} {miny}, {maxx} {maxy})'.format(
            #                 minx=minx, maxx=maxx, miny=miny, maxy=maxy
            #             )
            #     )

            #     n_points_in_tile = session.query(
            #             func.sum(MapobjectSegmentation.geom_poly.ST_NPoints())
            #         ).\
            #         filter(
            #             MapobjectSegmentation.id.in_(mapobject_outline_ids),
            #             MapobjectSegmentation.geom_poly.intersects(tile)
            #         ).\
            #         scalar()

            #     if n_points_in_tile is not None:
            #         n_points_in_tile_samples.append(n_points_in_tile)
            #     else:
            #         n_points_in_tile_samples.append(0)

            # n_points_in_tile_per_z[z] = int(
            #     float(sum(n_points_in_tile_samples)) /
            #     len(n_points_in_tile_samples)
            # )

        # min_poly_zoom = min([
            # z for z, n in n_points_in_tile_per_z.items()
            # if n <= n_points_per_tile_limit
        # ])
        # TODO: calculate the optimal zoom level
        if self.is_static:
            min_poly_zoom = 0
            max_poly_zoom = 0
        else:
            min_poly_zoom = maxzoom_level - 4
            min_poly_zoom = 0 if min_poly_zoom < 0 else min_poly_zoom
            max_poly_zoom = min_poly_zoom - 2
            max_poly_zoom = 0 if max_poly_zoom < 0 else max_poly_zoom
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


class Mapobject(ExperimentModel):

    '''A *map object* represents a connected pixel component in an
    image. It has outlines for drawing on the map and may also be associated
    with measurements (*features*), which can be queried or used for analysis.

    Attributes
    ----------
    mapobject_type_id: int
        ID of the parent mapobject
    mapobject_type: tmlib.models.MapobjectType
        parent mapobject type to which the mapobject belongs
    parent_id: int, optional
        ID of the parent mapobject
    segmentations: List[tmlib.models.MapobjectSegmentations]
        segmentations that belong to the mapobject
    feature_values: List[tmlib.models.FeatureValues]
        feature values that belong to the mapobject
    '''

    #: str: name of the corresponding database table
    __tablename__ = 'mapobjects'

    __distribute_by_hash__ = 'id'

    # Table columns
    parent_id = Column(Integer, index=True)
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

    def __init__(self, mapobject_type_id, parent_id=None):
        '''
        Parameters
        ----------
        mapobject_type_id: int
            ID of the parent mapobject type
        parent_id: int, optional
            ID of the parent mapobject
        '''
        self.mapobject_type_id = mapobject_type_id
        self.parent_id = parent_id

    def __repr__(self):
        return '<Mapobject(id=%d, type=%s)>' % (self.id, mapobject_type.name)


class MapobjectSegmentation(ExperimentModel):

    '''A *mapobject segmentation* provides the geographic representation
    of a *mapobject* and associates it with the corresponding image acquisition
    *site* in which the object was identified.

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
    pipeline: str
            name of the corresponding Jterator pipeline in which the objects
            were segmented
    site_id: int
        ID of the parent site
    site: tmlib.models.Site
        site to which the segmentation belongs
    is_border: bool
        whether the object touches at the border of a *site* and is
        therefore only partially represented on the corresponding image
    label: int
        one-based object identifier number which is unique per site
    mapobject_id: int
        ID of parent mapobject
    mapobject: tmlib.models.Mapobject
        parent mapobject to which the outline belongs

    '''

    #: str: name of the corresponding database table
    __tablename__ = 'mapobject_segmentations'

    __table_args__ = (
        UniqueConstraint('label', 'tpoint', 'zplane', 'site_id', 'mapobject_id'),
    )

    __distribute_by_hash__ = 'mapobject_id'

    # Table columns
    is_border = Column(Boolean, index=True)
    label = Column(Integer, index=True)
    pipeline = Column(String, index=True)
    tpoint = Column(Integer, index=True)
    zplane = Column(Integer, index=True)
    geom_poly = Column(Geometry('POLYGON'), index=True)
    geom_centroid = Column(Geometry('POINT'), index=True)
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
            'segmentations', cascade='all, delete-orphan'
        )
    )

    def __init__(self, geom_poly, geom_centroid, mapobject_id, label=None,
            is_border=None, tpoint=None, zplane=None, pipeline=None, site_id=None):
        '''
        Parameters
        ----------
        geom_poly: str
            EWKT polygon geometry representing the outline of the mapobject
        geom_centroid: str
            EWKT point geometry representing the centriod of the mapobject
        mapobject_id: int
            ID of parent mapobject
        label: int, optional
            one-based object identifier number which is unique per site
        is_border: bool, optional
            whether the object touches at the border of a *site* and is
            therefore only partially represented on the corresponding image
        tpoint: int, optional
            time point index
        zplane: int, optional
            z-plane index
        pipeline: str, optional
            name of the corresponding Jterator pipeline that was used to
            segment the mapobjects
        site_id: int, optional
            ID of the parent site

        Note
        ----
        Static mapobjects (e.g. "Wells") are neither associated with a particular
        image acquisition site (they actually enclose several sites) nor with
        a time point or z-resolution level.

        Warning
        -------
        The segmentation may be used to reconstruct the original label image,
        but there might be a bias, depending on the level of simplification
        applied upon generation of the outlines.
        '''
        self.tpoint = tpoint
        self.zplane = zplane
        self.mapobject_id = mapobject_id
        self.geom_poly = geom_poly
        self.geom_centroid = geom_centroid
        self.is_border = is_border
        self.pipeline = pipeline
        self.site_id = site_id

    @staticmethod
    def bounding_box(x, y, z, maxzoom):
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

        Returns
        -------
        Tuple[int]
            bounding box coordinates (x_top, y_top, x_bottom, y_bottom)
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
        minx, miny, maxx, maxy = MapobjectSegmentation.bounding_box(x, y, z, maxzoom)
        # TODO: use shapely to create objects
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

        spatial_filter = (MapobjectSegmentation.geom_poly.ST_Intersects(tile))
        if x != 0:
            spatial_filter = spatial_filter & \
                not_(ST_ExteriorRing(MapobjectSegmentation.geom_poly).\
                     ST_Intersects(left_border))
        if y != 0:
            spatial_filter = spatial_filter & \
                not_(ST_ExteriorRing(MapobjectSegmentation.geom_poly).\
                     ST_Intersects(top_border))

        return spatial_filter

    def __repr__(self):
        return (
            '<%s('
                'id=%d, label=%r, tpoint=%r, zplane=%r, site_id=%r, mapobject_id=%r'
            ')>'
            % (self.__class__.__name__, self.id, self.label, self.tpoint,
                self.zplane, self.site_id, self.mapobject_id)
        )
