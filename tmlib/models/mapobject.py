# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import json
import os
import logging
import random
import collections

import pandas as pd
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from sqlalchemy.orm import Session
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, not_
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import UniqueConstraint

from tmlib.models.base import ExperimentModel, DateMixIn
from tmlib.models.types import ST_ExteriorRing
from tmlib.utils import autocreate_directory_property

logger = logging.getLogger(__name__)


class MapobjectType(ExperimentModel):

    '''A *mapobject type* represents a conceptual group of *mapobjects*
    (segmented objects) that reflect different biological entities,
    such as "cells" or "nuclei" for example.

    Attributes
    ----------
    mapobjects: List[tmlib.models.mapobject.Mapobject]
        mapobjects belonging to the mapobject type
    '''

    __tablename__ = 'mapobject_types'

    __distribute_by_replication__ = True

    __table_args__ = (UniqueConstraint('name'), )

    _max_poly_zoom = Column('max_poly_zoom', Integer)
    _min_poly_zoom = Column('min_poly_zoom', Integer)

    #: str: name given by user
    name = Column(String, index=True, nullable=False)

    #: bool: whether object outlines are static, i.e. don't depend on
    #: image analysis (examples are "plates" or "wells")
    is_static = Column(Boolean, index=True)

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
        self.experiment_id = 1

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
        logger.debug('get mapobject outlines falling into tile')
        maxzoom = self.experiment.channels[0].layers[0].maxzoom_level_index

        session = Session.object_session(self)

        do_simplify = self.max_poly_zoom <= z < self.min_poly_zoom
        do_nothing = z < self.max_poly_zoom
        if do_simplify:
            logger.debug('represent object by centroid')
            select_stmt = session.query(
                MapobjectSegmentation.mapobject_id,
                MapobjectSegmentation.geom_centroid.ST_AsGeoJSON())
        elif do_nothing:
            logger.debug('dont\'t represent object')
            return list()
        else:
            logger.debug('represent object as polygon')
            select_stmt = session.query(
                MapobjectSegmentation.mapobject_id,
                MapobjectSegmentation.geom_poly.ST_AsGeoJSON()
            )

        outlines = select_stmt.\
            join(Mapobject).\
            join(MapobjectType).\
            filter(
                (MapobjectType.id == self.id) &
                ((MapobjectType.is_static) |
                 (MapobjectSegmentation.tpoint == tpoint) &
                 (MapobjectSegmentation.zplane == zplane)
                ) &
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
            IDs of instances of :class:`tmlib.models.mapobject.MapobjectSegmentation`
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

    def get_feature_value_matrix(self, feature_names=[]):
        '''Gets a feature matrix for all mapobjects of this type.

        Parameters
        ----------
        feature_names: List[str], optional
            names of features that should be included (default: ``[]``);
            all features will be used by default

        Returns
        -------
        pandas.DataFrame
            *n*x*p* matrix, where *n* is the number of mapobjects and *p*
            the number of features.
            The index is set to the IDs of the mapobjects.

        Warning
        -------
        This may not be a good idea in case of a large experiment, because
        the data may not fit into memory.
        '''
        from tmlib.models import Feature, FeatureValue
        session = Session.object_session(self)
        if feature_names:
            feature_values = session.query(
                    Feature.name, FeatureValue.mapobject_id, FeatureValue.value
                ).\
                join(FeatureValue).\
                filter(
                    (Feature.name.in_(set(feature_names))) &
                    (Feature.mapobject_type_id == self.id)
                ).\
                order_by(FeatureValue.mapobject_id).\
                all()
        else:
            feature_values = session.query(
                Feature.name, FeatureValue.mapobject_id, FeatureValue.value).\
                join(FeatureValue).\
                filter(Feature.mapobject_type_id == self.id).\
                order_by(FeatureValue.mapobject_id).\
                all()

        feature_df_long = pd.DataFrame(feature_values)
        feature_df_long.columns = ['feature', 'mapobject', 'value']
        feature_df = pd.pivot_table(
            feature_df_long, values='value',
            index='mapobject', columns='feature'
        )
        return feature_df

    def get_metadata_matrix(self):
        '''Gets the metadata for all mapobjects of this type.

        Returns
        -------
        pandas.DataFrame
            *n*x*q* matrix, where *n* is the number of mapobjects and *q*
            the number of metadata attributes.
            The index is set to the IDs of the mapobjects.
        '''
        from tmlib.models import Plate, Well, Site
        session = Session.object_session(self)
        metadata = pd.DataFrame(
            session.query(
                MapobjectSegmentation.tpoint,
                MapobjectSegmentation.zplane,
                Plate.name,
                Well.name,
                Site.y,
                Site.x,
                MapobjectSegmentation.label,
                MapobjectSegmentation.mapobject_id
            ).\
            join(Mapobject).\
            join(Site).\
            join(Well).\
            join(Plate).\
            filter(Mapobject.mapobject_type_id == self.id).\
            order_by(Mapobject.id).\
            all()
        )
        metadata.columns = [
            'tpoint', 'zplane', 'plate', 'well', 'y', 'x', 'label', 'mapobject'
        ]
        metadata.sort(['mapobject'], inplace=True)
        metadata.set_index('mapobject', inplace=True)
        return metadata

    def __repr__(self):
        return '<MapobjectType(id=%d, name=%r)>' % (self.id, self.name)


class Mapobject(ExperimentModel):

    '''A *map object* represents a connected pixel component in an
    image. It has outlines for drawing on the map and may also be associated
    with measurements (*features*), which can be queried or used for analysis.

    '''

    #: str: name of the corresponding database table
    __tablename__ = 'mapobjects'

    __distribute_by_hash__ = 'id'

    #: int: ID of another mapobject from which the object is derived from
    #: (relevent for tracking of proliferating cells for example)
    parent_id = Column(Integer, index=True)

    #: int: ID of parent mapobject type
    mapobject_type_id = Column(Integer, index=True, nullable=False)

    # mapobject_type_id = Column(
    #     Integer,
    #     ForeignKey('mapobject_types.id', ondelete='CASCADE'),
    #     index=True
    # )

    # #: tmlib.models.mapobject.MapobjecType: parent mapobject type
    # mapobject_type = relationship(
    #     'MapobjectType',
    #     backref=backref('mapobjects', cascade='all, delete-orphan')
    # )

    # #: List[tmlib.models.MapobjectSegmentation]: segmentations belonging to
    # #: the mapobject
    # segmentations = relationship(
    #     'MapobjectSegmentation',
    #     backref=backref(
    #         'mapobject', cascade='all, delete-orphan', single_parent=True
    #     )
    # )

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
        return '<Mapobject(id=%d, type=%s)>' % (
            self.id, self.mapobject_type.name
        )


class MapobjectSegmentation(ExperimentModel):

    '''A *mapobject segmentation* provides the geographic representation
    of a :class:`Mapobject <tmlib.models.mapobject.Mapobject>` and associates
    it with the corresponding :class:`Site <tmlib.models.site.Site>`
    in which the object was identified.

    '''

    __tablename__ = 'mapobject_segmentations'

    __table_args__ = (
        UniqueConstraint('label', 'tpoint', 'zplane', 'site_id', 'mapobject_id'),
    )

    __distribute_by_hash__ = 'mapobject_id'

    #: bool: whether the object lies at the border of an image
    is_border = Column(Boolean, index=True)

    #: int: value assigned to the object in a label image
    label = Column(Integer, index=True)

    #: str: name of the corresponding Jterator pipeline that created the
    #: segmentation
    pipeline = Column(String, index=True)

    #: int: zero-based index in time series
    tpoint = Column(Integer, index=True)

    #: int: zero-based index in z stack
    zplane = Column(Integer, index=True)

    #: EWKT polygon geometry
    geom_poly = Column(Geometry('POLYGON'))

    #: EWKT entroid geometry
    geom_centroid = Column(Geometry('POINT'))

    #: int: ID of parent site
    site_id = Column(Integer, index=True, nullable=False)

    #: int: ID of parent mapobject
    mapobject_id = Column(Integer, index=True, nullable=False)

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
            minx=minx, maxx=maxx, miny=miny, maxy=maxy
        )
        # The outlines should not lie on the top or left border since this
        # would otherwise lead to requests for neighboring tiles receiving
        # the same objects.
        # This in turn leads to overplotting and is noticeable when the objects
        # have a fill color with an opacity != 0 or != 1.
        top_border = 'LINESTRING({minx} {maxy}, {maxx} {maxy})'.format(
            minx=minx, maxx=maxx, maxy=maxy
        )
        left_border = 'LINESTRING({minx} {maxy}, {minx} {miny})'.format(
            minx=minx, maxy=maxy, miny=miny
        )

        spatial_filter = (MapobjectSegmentation.geom_poly.ST_Intersects(tile))
        if x != 0:
            spatial_filter = spatial_filter & \
                not_(ST_ExteriorRing(MapobjectSegmentation.geom_poly).\
                     ST_Intersects(left_border)
                )
        if y != 0:
            spatial_filter = spatial_filter & \
                not_(ST_ExteriorRing(MapobjectSegmentation.geom_poly).\
                     ST_Intersects(top_border)
                )

        return spatial_filter

    def __repr__(self):
        return (
            '<%s('
                'id=%d, label=%r, tpoint=%r, zplane=%r, site_id=%r, mapobject_id=%r'
            ')>'
            % (self.__class__.__name__, self.id, self.label, self.tpoint,
                self.zplane, self.site_id, self.mapobject_id)
        )
