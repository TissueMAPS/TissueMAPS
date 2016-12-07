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

from tmlib import cfg
from tmlib.models.base import ExperimentModel, DateMixIn
from tmlib.models.result import ToolResult
from tmlib.models.utils import ExperimentConnection, ExperimentSession
from tmlib.models.feature import Feature
from tmlib.utils import autocreate_directory_property

logger = logging.getLogger(__name__)


class MapobjectType(ExperimentModel):

    '''A *mapobject type* represents a conceptual group of *mapobjects*
    (segmented objects) that reflect different biological entities,
    such as "cells" or "nuclei" for example.

    Attributes
    ----------
    results: List[tmlib.models.result.ToolResult]
        results belonging to the mapobject type
    features: List[tmlib.models.feature.Feature]
        features belonging to the mapobject type
    '''

    __tablename__ = 'mapobject_types'

    __table_args__ = (UniqueConstraint('name'), )

    _max_poly_zoom = Column('max_poly_zoom', Integer)
    _min_poly_zoom = Column('min_poly_zoom', Integer)

    #: str: name given by user
    name = Column(String, index=True, nullable=False)

    #: bool: whether object outlines are static, i.e. don't depend on
    #: image analysis (examples are "plates" or "wells")
    is_static = Column(Boolean, index=True)

    #: int: ID of parent experiment
    experiment_id = Column(
        Integer,
        ForeignKey('experiment.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    #: tmlib.models.experiment.Experiment: parent experiment
    experiment = relationship(
        'Experiment',
        backref=backref('mapobject_types', cascade='all, delete-orphan')
    )

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

    def calculate_min_max_poly_zoom(self, maxzoom_level):
        '''Calculates the minimum zoom level above which mapobjects are
        represented on the map as polygons instead of centroids and the
        maximum zoom level below which mapobjects are no longer visualized.

        Parameters
        ----------
        maxzoom_level: int
            maximum zoom level of the pyramid

        Returns
        -------
        Tuple[int]
            minimal and maximal zoom level
        '''
        # TODO: this is too simplistic
        if self.is_static:
            min_poly_zoom = 0
            max_poly_zoom = 0
        else:
            min_poly_zoom = maxzoom_level - 4
            min_poly_zoom = 0 if min_poly_zoom < 0 else min_poly_zoom
            max_poly_zoom = min_poly_zoom - 2
            max_poly_zoom = 0 if max_poly_zoom < 0 else max_poly_zoom
        return (min_poly_zoom, max_poly_zoom)

    # def get_feature_value_matrix(self, feature_names=[]):
    #     '''Gets a feature matrix for all mapobjects of this type.

    #     Parameters
    #     ----------
    #     feature_names: List[str], optional
    #         names of features that should be included (default: ``[]``);
    #         all features will be used by default

    #     Returns
    #     -------
    #     pandas.DataFrame
    #         *n*x*p* matrix, where *n* is the number of mapobjects and *p*
    #         the number of features.
    #         The index is set to the IDs of the mapobjects.

    #     Warning
    #     -------
    #     This may not be a good idea in case of a large experiment, because
    #     the data may not fit into memory.
    #     '''
    #     from tmlib.models import Feature, FeatureValue
    #     session = Session.object_session(self)
    #     if feature_names:
    #         feature_values = session.query(
    #                 Feature.name, FeatureValue.mapobject_id, FeatureValue.value
    #             ).\
    #             join(FeatureValue).\
    #             filter(
    #                 (Feature.name.in_(set(feature_names))) &
    #                 (Feature.mapobject_type_id == self.id)
    #             ).\
    #             order_by(FeatureValue.mapobject_id).\
    #             all()
    #     else:
    #         feature_values = session.query(
    #             Feature.name, FeatureValue.mapobject_id, FeatureValue.value).\
    #             join(FeatureValue).\
    #             filter(Feature.mapobject_type_id == self.id).\
    #             order_by(FeatureValue.mapobject_id).\
    #             all()

    #     feature_df_long = pd.DataFrame(feature_values)
    #     feature_df_long.columns = ['feature', 'mapobject', 'value']
    #     feature_df = pd.pivot_table(
    #         feature_df_long, values='value',
    #         index='mapobject', columns='feature'
    #     )
    #     return feature_df

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
    tpoint = Column(Integer, index=True, nullable=False)

    #: int: zero-based index in z stack
    zplane = Column(Integer, index=True, nullable=False)

    #: EWKT polygon geometry
    geom_poly = Column(Geometry('POLYGON'))

    #: EWKT entroid geometry
    geom_centroid = Column(Geometry('POINT'))

    #: int: ID of parent site
    site_id = Column(Integer, index=True)

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
            horizontal tile coordinate
        y: int
            vertical tile coordinate
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

    def __repr__(self):
        return (
            '<%s('
                'id=%d, label=%r, tpoint=%r, zplane=%r, site_id=%r, mapobject_id=%r'
            ')>'
            % (self.__class__.__name__, self.id, self.label, self.tpoint,
                self.zplane, self.site_id, self.mapobject_id)
        )


def delete_mapobject_types_cascade(experiment_id, is_static,
        site_id=None, pipeline=None):
    '''Deletes all instances of
    :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>` as well as
    as "children" instances of
    :class:`Mapobject <tmlib.models.mapobject.Mapobject>`,
    :class:`MapobjectSegmentation <tmlib.models.mapobject.MapobjectSegmentation>`
    :class:`Feature <tmlib.models.feature.Feature>`,
    :class:`ToolResult <tmlib.models.result.ToolResult>`,
    :class:`LabelLayer <tmlib.models.layer.LabelLayer>`,
    :class:`FeatureValue <tmlib.models.feature.FeatureValue>` and
    :class:`LabelValue <tmlib.models.feature.LabelValue>`.

    Parameters
    ----------
    experiment_id: int
        ID of the parent :class:`Experiment <tmlib.models.experiment.Experiment>`
    is_static: bool
        whether mapojbects of *static* types should be deleted
    site_id: int, optional
        ID of the parent :class:`Site <tmlib.models.site.Site>`
    pipeline: str, optional
        the pipeline in which mapobjects were genereated
        (not required for non-*static* mapobject types)

    Note
    ----
    This is not possible via the standard *SQLAlchemy* approach, because the
    tables of :class:`Mapobject <tmlib.models.mapobject.Mapobject>` and
    :class:`MapobjectSegmentation <tmlib.models.mapobject.MapobjectSegmentation>`
    might be distributed over a cluster.
    '''
    with ExperimentSession(experiment_id) as session:
        mapobject_types = session.query(MapobjectType).\
            filter(MapobjectType.is_static == is_static).\
            all()
        mapobject_type_ids = [t.id for t in mapobject_types]

    delete_mapobjects_cascade(
        experiment_id, mapobject_type_ids, site_id, pipeline
    )

    if mapobject_type_ids:
        with ExperimentSession(experiment_id) as session:
            logger.info('delete mapobject types')
            session.query(MapobjectType).\
                filter(MapobjectType.id.in_(mapobject_type_ids)).\
                delete()


def _compile_distributed_query(sql):
    # This is required for modification of distributed tables
    # TODO: alter queries in "citus" dialect
    if cfg.db_driver == 'citus':
        return '''
            SELECT master_modify_multiple_shards('
                {query}
            ')
        '''.format(query=sql)
    else:
        return sql


def _delete_mapobjects_cascade(experiment_id, mapobject_ids):
    # NOTE: Using ANY with an ARRAY is more performant than using IN.
    if mapobject_ids:
        with ExperimentConnection(experiment_id) as connection:

            logger.info('delete mapobject segmentations')
            sql = '''
                DELETE FROM mapobject_segmentations s
                WHERE mapobject_id = ANY(%(mapobject_ids)s);
            '''
            connection.execute(
                _compile_distributed_query(sql), {
                'mapobject_ids': mapobject_ids
            })

            logger.info('delete feature values')
            sql = '''
                DELETE FROM feature_values
                WHERE mapobject_id = ANY(%(mapobject_ids)s);
            '''
            connection.execute(
                _compile_distributed_query(sql), {
                'mapobject_ids': mapobject_ids
            })

            logger.info('delete label values')
            sql = '''
                DELETE FROM label_values
                WHERE mapobject_id = ANY(%(mapobject_ids)s);
            '''
            connection.execute(
                _compile_distributed_query(sql), {
                'mapobject_ids': mapobject_ids
            })

            logger.info('delete mapobjects')
            sql = '''
                DELETE FROM mapobjects
                WHERE id = ANY(%(mapobject_ids)s);
            '''
            connection.execute(
                _compile_distributed_query(sql), {
                'mapobject_ids': mapobject_ids
            })


def delete_mapobjects_cascade(experiment_id, mapobject_type_ids,
        site_id=None, pipeline=None):
    '''Deletes all instances of
    :class:`Mapobject <tmlib.models.mapobject.Mapobject>` as well as all
    "children" instances of
    :class:`MapobjectSegmentation <tmlib.models.mapobject.MapobjectSegmentation>`
    :class:`FeatureValue <tmlib.models.feature.FeatureValue>`,
    :class:`LabelValue <tmlib.models.feature.LabelValue>`.

    Parameters
    ----------
    experiment_id: int
        ID of the parent :class:`Experiment <tmlib.models.experiment.Experiment>`
    mapobject_type_ids: List[int]
        IDs of parent :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`
    site_id: int, optional
        ID of the parent :class:`Site <tmlib.models.site.Site>`
    pipeline: str, optional
        the pipeline in which mapobjects were genereated
        (not required for non-*static* mapobject types)

    Note
    ----
    This is not possible via the standard *SQLAlchemy* approach, because the
    tables of :class:`Mapobject <tmlib.models.mapobject.Mapobject>` and
    :class:`MapobjectSegmentation <tmlib.models.mapobject.MapobjectSegmentation>`
    might be distributed over a cluster.
    '''
    if mapobject_type_ids:
        with ExperimentConnection(experiment_id) as connection:
            sql = '''
                SELECT m.id FROM mapobjects m
                JOIN mapobject_segmentations s ON s.mapobject_id = m.id
                WHERE m.mapobject_type_id = ANY(%(mapobject_type_ids)s)
            '''
            if site_id is not None:
                sql += '''
                    AND s.site_id = %(site_id)s
                '''
            if pipeline is not None:
                sql += '''
                    AND s.pipeline = %(pipeline)s
                '''
            connection.execute(sql, {
                'site_id': site_id,
                'pipeline': pipeline,
                'mapobject_type_ids': mapobject_type_ids
            })
            mapobjects = connection.fetchall()
            mapobject_ids = [m.id for m in mapobjects]

        _delete_mapobjects_cascade(experiment_id, mapobject_ids)


def delete_invalid_mapobjects_cascade(experiment_id):
    '''Deletes all instances of
    :class:`Mapobject <tmlib.models.mapobject.Mapobject>` with invalid
    geometries as well as all "children" instances of
    :class:`MapobjectSegmentation <tmlib.models.mapobject.MapobjectSegmentation>`
    :class:`FeatureValue <tmlib.models.feature.FeatureValue>`,
    :class:`LabelValue <tmlib.models.feature.LabelValue>`.

    Parameters
    ----------
    experiment_id: int
        ID of the parent :class:`Experiment <tmlib.models.experiment.Experiment>`

    Note
    ----
    This is not possible via the standard *SQLAlchemy* approach, because the
    tables of :class:`Mapobject <tmlib.models.mapobject.Mapobject>` and
    :class:`MapobjectSegmentation <tmlib.models.mapobject.MapobjectSegmentation>`
    might be distributed over a cluster.
    '''
    with ExperimentConnection(experiment_id) as connection:
        connection.execute('''
            SELECT mapobject_id FROM mapobject_segmentations
            WHERE NOT ST_IsValid(geom_poly);
        ''')
        mapobject_segm = connection.fetchall()
        mapobject_ids = [s.mapobject_id for s in mapobject_segm]

    _delete_mapobjects_cascade(experiment_id, mapobject_ids)


def get_mapobject_outlines_within_tile(experiment_id, mapobject_type_name,
        x, y, z, tpoint, zplane):
    '''Get outlines of all objects that fall within a given pyramid tile.

    Parameters
    ----------
    experiment_id: int
        ID of the parent :class:`Experiment <tmlib.models.experiment.Experiment>`
    mapobject_type_name: str
        name of the :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`
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
    with ExperimentConnection(experiment_id) as connection:
        # NOTE: Column "depth" is implemented as a hybrid_property on the
        # data model class. The property must have been accessed once for this
        # query to work.
        connection.execute('''
            SELECT depth FROM channel_layers
            LIMIT 1
        ''')
        layer = connection.fetchone()
        maxzoom = layer.depth - 1

        connection.execute('''
            SELECT id, is_static, min_poly_zoom, max_poly_zoom
            FROM mapobject_types
            WHERE name = %(name)s;
        ''', {
            'name': mapobject_type_name
        })
        mapobject_type_id, is_static, min_poly_zoom, max_poly_zoom = \
            connection.fetchone()
        do_simplify = max_poly_zoom <= z < min_poly_zoom
        do_nothing = z < max_poly_zoom
        min_x, min_y, max_x, max_y = MapobjectSegmentation.bounding_box(
            x, y, z, maxzoom
        )
        if do_nothing:
            logger.debug('dont\'t represent objects')
            return list()
        elif do_simplify:
            logger.debug('represent objects as centroid')
            sql = '''
                SELECT s.mapobject_id, ST_AsGeoJSON(s.geom_centroid)
            '''
        else:
            logger.debug('represent objects as polygon')
            sql = '''
                SELECT s.mapobject_id, ST_AsGeoJSON(s.geom_poly)
            '''

        # The outlines should not lie on the top or left border since
        # this would otherwise lead to requests for neighboring tiles
        # receiving the same objects.
        # This in turn leads to overplotting and is noticeable
        # when the objects have a fill color with an opacity != 0 or != 1.
        sql += '''
            FROM mapobject_segmentations s
            JOIN mapobjects m ON m.id = s.mapobject_id
            WHERE m.mapobject_type_id = %(mapobject_type_id)s
            AND ST_Intersects(
                    s.geom_poly,
                    ST_GeomFromText(
                        'POLYGON((
                            %(max_x)s %(max_y)s, %(min_x)s %(max_y)s,
                            %(min_x)s %(min_y)s, %(max_x)s %(min_y)s,
                            %(max_x)s %(max_y)s
                        ))'
                    )
                )
        '''
        if not is_static:
            sql += '''
                AND s.tpoint = %(tpoint)s
                AND s.zplane = %(zplane)s
                AND CASE
                    WHEN %(not_left_border_tile)s THEN
                        ST_Disjoint(
                            ST_ExteriorRing(s.geom_poly),
                            ST_GeomFromText(
                                'LINESTRING(
                                    %(min_x)s %(max_y)s, %(min_x)s %(min_y)s
                                )'
                            )
                        )
                    ELSE
                        TRUE
                    END
                AND CASE
                    WHEN %(not_top_border_tile)s THEN
                        ST_Disjoint(
                            ST_ExteriorRing(s.geom_poly),
                            ST_GeomFromText(
                                'LINESTRING(
                                    %(min_x)s %(max_y)s, %(max_x)s %(max_y)s
                                )'
                            )
                        )
                    ELSE
                        TRUE
                    END
            '''
        connection.execute(sql, {
            'is_static': is_static,
            'mapobject_type_id': mapobject_type_id,
            'tpoint': tpoint, 'zplane': zplane,
            'not_top_border_tile': x != 0, 'not_left_border_tile': y != 0,
            'min_x': min_x, 'max_x': max_x, 'min_y': min_y, 'max_y': max_y
        })

        outlines = connection.fetchall()
        if len(outlines) == 0:
            logger.warn(
                'no outlines found for objects of type "%s" within tile: '
                'x=%d, y=%d, z=%d, tpoint=%d, zplane=%d',
                mapobject_type_name, x, y, z, tpoint, zplane
            )

        return outlines

