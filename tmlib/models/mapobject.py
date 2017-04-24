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
from sqlalchemy import (
    Column, String, Integer, Boolean, ForeignKey, not_, Index,
    UniqueConstraint, PrimaryKeyConstraint
)
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property

from tmlib import cfg
from tmlib.models.base import ExperimentModel, DateMixIn
from tmlib.models.dialect import compile_distributed_query
from tmlib.models.result import ToolResult, LabelValues
from tmlib.models.utils import ExperimentConnection, ExperimentSession
from tmlib.models.feature import Feature, FeatureValues
from tmlib.models.types import ST_SimplifyPreserveTopology
from tmlib.models.site import Site
from tmlib.utils import autocreate_directory_property, create_partitions

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

    #: str: name given by user
    name = Column(String(50), index=True, nullable=False)

    #: str: name of another type that serves as a reference for "static"
    #: mapobjects, i.e. objects that are pre-defined through the experiment
    #: layout and independent of image segmentation (e.g. "Plate" or "Well")
    ref_type = Column(String(50))

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

    def __init__(self, name, experiment_id, ref_type=None):
        '''
        Parameters
        ----------
        name: str
            name of the map objects type, e.g. "cells"
        experiment_id: int
            ID of the parent
            :class:`Experiment <tmlib.models.experiment.Experiment>`
        ref_type: str, optional
            name of another reference type (default: ``None``)
        '''
        self.name = name
        self.ref_type = ref_type
        self.experiment_id = experiment_id

    @classmethod
    def delete_cascade(cls, connection, ref_type=None, id=None):
        '''Deletes all instances as well as "children"
        instances of :class:`Mapobject <tmlib.models.mapobject.Mapobject>`,
        :class:`MapobjectSegmentation <tmlib.models.mapobject.MapobjectSegmentation>`,
        :class:`Feature <tmlib.models.feature.Feature>`,
        :class:`FeatureValues <tmlib.models.feature.FeatureValues>`,
        :class:`ToolResult <tmlib.models.result.ToolResult>`,
        :class:`LabelLayer <tmlib.models.layer.LabelLayer>` and
        :class:`LabelValues <tmlib.models.feature.LabelValues>`.

        Parameters
        ----------
        connection: psycopg2.extras.NamedTupleCursor
            experiment-specific database connection created via
            :class:`ExperimentConnection <tmlib.models.utils.ExperimentConnection>`
        ref_type: str, optional
            name of reference type (if ``"NULL"`` all mapobject types without
            a `ref_type` will be deleted)
        id: int, optional
            ID of a specific mapobject type that should be deleted

        '''
        if ref_type is 'NULL':
            logger.debug('delete non-static mapobjects')
            connection.execute('''
                SELECT id, name FROM mapobject_types
                WHERE ref_type IS NULL;
            ''')
            mapobject_type = connection.fetchone()
            if mapobject_type:
                logger.debug(
                    'delete mapobjects of type "%s"', mapobject_type.name
                )
                Mapobject.delete_cascade(connection, mapobject_type.id)
                logger.debug('delete mapobject type %s', mapobject_type.name)
                connection.execute('''
                    DELETE FROM mapobject_types WHERE id = %(id)s;
                ''', {
                    'id': mapobject_type.id
                })
        elif ref_type is not None:
            logger.debug('delete static mapobjects referencing "%s"', ref_type)
            connection.execute('''
                SELECT id, name FROM mapobject_types
                WHERE ref_type = %(ref_type)s
            ''', {
                'ref_type': ref_type
            })
            mapobject_type = connection.fetchone()
            if mapobject_type:
                logger.debug(
                    'delete mapobjects of type "%s"', mapobject_type.name
                )
                Mapobject.delete_cascade(connection, mapobject_type.id)
                logger.debug('delete mapobject type %s', mapobject_type.name)
                connection.execute('''
                    DELETE FROM mapobject_types WHERE id = %(id)s;
                ''', {
                    'id': mapobject_type.id
                })
        elif id is not None:
            logger.debug('delete mapobjects of type %d', id)
            Mapobject.delete_cascade(connection, id)
            logger.debug('delete mapobject type %d', id)
            connection.execute('''
                DELETE FROM mapobject_types WHERE id = %(id)s;
            ''', {
                'id': id
            })
        else:
            logger.debug('delete all mapobjects')
            Mapobject.delete_cascade(connection)
            logger.debug('delete all mapobject types')
            connection.execute('DELETE FROM mapobject_types;')

    def get_segmentations_per_site(self, site_id, tpoints=None, zplanes=None,
            as_polygons=True):
        '''Gets each
        :class:`MapobjectSegmentation <tmlib.models.mapobject.MapobjectSegmentation>`
        that intersects with a given site.

        Parameters
        ----------
        site_id: int
            ID of a given :class:`Site <tmlib.models.site.Site>`
        tpoints: List[int], optional
            time points for which segmentations should be filtered
            (default: ``None``)
        zplanes: List[int], optional
            z-planes for which segmentations should be filtered
            (default: ``None``)
        as_polygons: bool, optional
            whether segmentations should be returned as polygons;
            if ``False`` segmentations will be returned as points
            (default: ``True``)

        Returns
        -------
        List[List[Tuple[Union[int, shapely.geometry.polygon.Polygon, shapely.geometry.point.Point]]]]
            label and geometry of segmentated objects for each z-plane
            and time point
        '''
        session = Session.object_session(self)
        site_mapobject_type = session.query(MapobjectType).\
            filter_by(ref_type=Site.__name__).\
            one()
        site_segmentation = session.query(MapobjectSegmentation).\
            join(Mapobject).\
            filter(
                Mapobject.ref_id == site_id,
                Mapobject.mapobject_type_id == site_mapobject_type.id
            ).\
            one()

        segmentation_layers = session.query(SegmentationLayer).\
            filter_by(mapobject_type_id=self.id)
        if tpoints:
            segmentation_layers = segmentation_layers.\
                filter(SegmentationLayer.tpoint.in_(tpoints))
        if zplanes:
            segmentation_layers = segmentation_layers.\
                filter(SegmentationLayer.zplane.in_(zplanes))

        polygons = collections.defaultdict(list)
        for layer in segmentation_layers.\
            order_by(SegmentationLayer.tpoint, SegmentationLayer.zplane):
            if as_polygons:
                segmentations = session.query(
                        MapobjectSegmentation.label,
                        MapobjectSegmentation.geom_polygon
                    )
            else:
                segmentations = session.query(
                        MapobjectSegmentation.label,
                        MapobjectSegmentation.geom_centroid
                    )
            segmentations = segmentations.\
                join(Mapobject).\
                filter(
                    Mapobject.mapobject_type_id == self.id,
                    MapobjectSegmentation.segmentation_layer_id == layer.id,
                    MapobjectSegmentation.geom_centroid.ST_Intersects(
                        site_segmentation.geom_polygon
                    )
                ).\
                all()
            polygons[layer.tpoint].append(segmentations)

        return [polygons[k] for k in sorted(polygons.keys())]

    def __repr__(self):
        return '<MapobjectType(id=%d, name=%r)>' % (self.id, self.name)


class Mapobject(ExperimentModel):

    '''A *mapobject* represents a connected pixel component in an
    image. It has one or more 2D segmentations that can be used to represent
    the object on the map and may also be associated with measurements
    (*features*), which can be queried or used for further analysis.
    '''

    #: str: name of the corresponding database table
    __tablename__ = 'mapobjects'

    __distribute_by_hash__ = 'id'

    #: int: ID of another record to which the object is related.
    #: This could refer to another mapobject in the same table, e.g. in order
    #: to track proliferating cells, or a record in another reference table,
    #: e.g. to identify the corresponding record of a "Well".
    ref_id = Column(Integer, index=True)

    #: int: ID of parent mapobject type
    mapobject_type_id = Column(Integer, index=True, nullable=False)

    def __init__(self, mapobject_type_id, ref_id=None):
        '''
        Parameters
        ----------
        mapobject_type_id: int
            ID of parent
            :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`
        ref_id: int, optional
            ID of the referenced record

        See also
        --------
        :attr:`tmlib.models.mapobject.MapobjectType.ref_type`
        '''
        self.mapobject_type_id = mapobject_type_id
        self.ref_id = ref_id

    @classmethod
    def _delete_cascade(cls, connection, mapobject_ids=None):
        logger.debug('delete mapobjects')
        if mapobject_ids is not None:
            # NOTE: Using ANY with an ARRAY is more performant than using IN.
            # TODO: Ideally we would like to join with mapobject_types.
            # However, at the moment there seems to be no way to DELETE entries
            # from a distributed table with a complex WHERE clause.
            # If the number of objects is too large this will lead to issues.
            # Therefore, we delete rows in batches.
            mapobject_id_partitions = create_partitions(mapobject_ids, 100000)
            # This will DELETE all records of referenced tables as well.
            sql = '''
                DELETE FROM mapobjects
                WHERE id = ANY(%(mapobject_ids)s);
            '''
            for mids in mapobject_id_partitions:
                connection.execute(
                    compile_distributed_query(sql), {
                    'mapobject_ids': mids
                })
        else:
            # Alternatively, we could also drop the tables and recreate them,
            # which may be faster. However, table distribution also takes time..
            connection.execute(
                compile_distributed_query('DELETE FROM mapobjects')
            )

    @classmethod
    def delete_invalid_cascade(cls, connection):
        '''Deletes all instances with invalid geometries as well as all
        "children" instances of
        :class:`MapobjectSegmentation <tmlib.models.mapobject.MapobjectSegmentation>`
        :class:`FeatureValues <tmlib.models.feature.FeatureValues>`,
        :class:`LabelValues <tmlib.models.feature.LabelValues>`.

        Parameters
        ----------
        connection: psycopg2.extras.NamedTupleCursor
            experiment-specific database connection created via
            :class:`ExperimentConnection <tmlib.models.utils.ExperimentConnection>`

        '''
        connection.execute('''
            SELECT mapobject_id FROM mapobject_segmentations
            WHERE NOT ST_IsValid(geom_polygon);
        ''')
        mapobject_segm = connection.fetchall()
        mapobject_ids = [s.mapobject_id for s in mapobject_segm]
        if mapobject_ids:
            cls._delete_cascade(connection, mapobject_ids)

    @classmethod
    def delete_missing_cascade(cls, connection):
        '''Deletes all instances with missing geometries as well as all
        "children" instances of
        :class:`MapobjectSegmentation <tmlib.models.mapobject.MapobjectSegmentation>`
        :class:`FeatureValues <tmlib.models.feature.FeatureValues>`,
        :class:`LabelValues <tmlib.models.feature.LabelValues>`.

        Parameters
        ----------
        connection: psycopg2.extras.NamedTupleCursor
            experiment-specific database connection created via
            :class:`ExperimentConnection <tmlib.models.utils.ExperimentConnection>`

        '''
        connection.execute('''
            SELECT m.id FROM mapobjects m
            LEFT OUTER JOIN mapobject_segmentations s
            ON m.id = s.mapobject_id
            WHERE s.id IS NULL;
        ''')
        mapobjects = connection.fetchall()
        mapobject_ids = [s.id for s in mapobjects]
        if mapobject_ids:
            cls._delete_cascade(connection, mapobject_ids)

    @classmethod
    def add(cls, connection, mapobject_type_id, ref_id=None):
        '''Adds a new record.

        Parameters
        ----------
        connection: psycopg2.extras.NamedTupleCursor
            experiment-specific database connection created via
            :class:`ExperimentConnection <tmlib.models.utils.ExperimentConnection>`
        mapobject_type_id: int
            ID of parent
            :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`
        ref_id: int, optional
            ID of reference mapobject

        Returns
        -------
        int
            ID of added record
        '''
        connection.execute('''
            SELECT nextval FROM nextval('mapobjects_id_seq');
        ''')
        record = connection.fetchone()
        mapobject_id = record.nextval
        connection.execute('''
            INSERT INTO mapobjects (id, mapobject_type_id, ref_id)
            VALUES (%(mapobject_id)s, %(mapobject_type_id)s, %(ref_id)s);
        ''', {
            'mapobject_id': mapobject_id,
            'mapobject_type_id': mapobject_type_id,
            'ref_id': ref_id
        })
        # TODO: Apparently, this doesn't insert in some cases???
        # INSERT INTO teams VALUES (...) RETURNING id INTO mapobject_id;
        return mapobject_id

    @classmethod
    def delete_cascade(cls, connection, mapobject_type_id=None,
            ref_type=None, ref_id=None):
        '''Deletes all instances as well as all "children" instances of
        :class:`MapobjectSegmentation <tmlib.models.mapobject.MapobjectSegmentation>`
        :class:`FeatureValues <tmlib.models.feature.FeatureValues>`,
        :class:`LabelValues <tmlib.models.feature.LabelValues>`.

        Parameters
        ----------
        connection: psycopg2.extras.NamedTupleCursor
            experiment-specific database connection created via
            :class:`ExperimentConnection <tmlib.models.utils.ExperimentConnection>`
        mapobject_type_id: int, optional
            ID of parent
            :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`
            by which mapobjects should be filtered
        ref_type: str, optional
            name of a reference type, e.g. "Site" that should be used for
            spatial filtering
        ref_id: int, optional
            ID of the reference object

        '''
        def get_ref_polygon(connection, ref_type, ref_id):
            logger.debug(
                'only delete mapobjects that intersect with the mapobject '
                'with ref_type="%s" and ref_id=%d', ref_type, ref_id
            )
            connection.execute('''
                SELECT id FROM mapobject_types
                WHERE ref_type = %(ref_type)s
            ''', {
                'ref_type': ref_type
            })
            mapobject_type = connection.fetchone()
            connection.execute('''
                SELECT s.geom_polygon FROM mapobjects m
                JOIN mapobject_segmentations s ON s.mapobject_id = m.id
                WHERE m.mapobject_type_id = %(mapobject_type_id)s
                AND m.ref_id = %(ref_id)s
            ''', {
                'mapobject_type_id': mapobject_type.id,
                'ref_id': ref_id
            })
            segmentation = connection.fetchone()
            return segmentation.geom_polygon

        if mapobject_type_id is not None:
            logger.debug(
                'delete mapobjects with mapobject_type_id=%d',
                mapobject_type_id
            )
            sql = '''
                SELECT m.id FROM mapobjects m
            '''
            if ref_type is not None and ref_id is not None:
                ref_polygon = get_ref_polygon(connection, ref_type, ref_id)
                sql += '''
                JOIN mapobject_segmentations s ON s.mapobject_id = m.id
                WHERE m.mapobject_type_id = %(mapobject_type_id)s
                AND ST_Intersects(s.geom_centroid, %(ref_polygon)s)
                '''
                connection.execute(sql, {
                    'ref_polygon': ref_polygon,
                    'mapobject_type_id': mapobject_type_id
                })
            else:
                sql += '''
                WHERE m.mapobject_type_id = %(mapobject_type_id)s
                '''
                connection.execute(sql, {
                    'mapobject_type_id': mapobject_type_id
                })
            mapobjects = connection.fetchall()
            mapobject_ids = [m.id for m in mapobjects]
            if mapobject_ids:
                cls._delete_cascade(connection, mapobject_ids)
        else:
            if ref_type is not None and ref_id is not None:
                ref_polygon = get_site_polygon(connection, ref_type, ref_id)
                connection.execute('''
                    SELECT m.id FROM mapobjects m
                    JOIN mapobject_segmentations s ON s.mapobject_id = m.id
                    WHERE ST_Intersects(s.geom_centroid, %(ref_polygon)s)
                ''', {
                    'ref_polygon': ref_polygon
                })
                mapobjects = connection.fetchall()
                mapobject_ids = [m.id for m in mapobjects]
                if mapobject_ids:
                    cls._delete_cascade(connection, mapobject_ids)
            else:
                cls._delete_cascade(connection)

    def __repr__(self):
        return '<Mapobject(id=%d, mapobject_type_id=%s)>' % (
            self.id, self.mapobject_type_id
        )


class MapobjectSegmentation(ExperimentModel):

    '''A *segmentation* provides the geometric representation
    of a :class:`Mapobject <tmlib.models.mapobject.Mapobject>`.
    '''

    __tablename__ = 'mapobject_segmentations'

    __table_args__ = (
        UniqueConstraint(
            'mapobject_id', 'segmentation_layer_id'
        ),
        Index(
            'ix_mapobject_segmentations_mapobject_id_segmentation_layer_id',
            'mapobject_id', 'segmentation_layer_id'
        )
    )

    __distribute_by_hash__ = 'mapobject_id'

    #: str: EWKT POLYGON geometry
    geom_polygon = Column(Geometry('POLYGON'))

    #: str: EWKT POINT geometry
    geom_centroid = Column(Geometry('POINT'), nullable=False)

    #: int: label assigned to the object upon segmentation
    label = Column(Integer)

    #: int: ID of parent mapobject
    mapobject_id = Column(
        Integer, ForeignKey('mapobjects.id', ondelete='CASCADE')
    )

    #: int: ID of parent segmentation layer
    segmentation_layer_id = Column(Integer, nullable=False)

    def __init__(self, geom_polygon, geom_centroid, mapobject_id,
            segmentation_layer_id, label=None):
        '''
        Parameters
        ----------
        geom_polygon: str
            EWKT POLYGON geometry representing the outline of the mapobject
        geom_centroid: str
            EWKT POINT geometry representing the centriod of the mapobject
        mapobject_id: int
            ID of parent :class:`Mapobject <tmlib.models.mapobject.Mapobject>`
        segmentation_layer_id: int
            ID of parent
            :class:`SegmentationLayer <tmlib.models.layer.SegmentationLayer>`
        label: int, optional
            label assigned to the segmented object
        '''
        self.geom_polygon = geom_polygon
        self.geom_centroid = geom_centroid
        self.mapobject_id = mapobject_id
        self.segmentation_layer_id = segmentation_layer_id
        self.label = label

    @classmethod
    def add(cls, connection, mapobject_id, segmentation_layer_id,
            polygon=None, centroid=None, label=None):
        '''Adds a new record.

        Parameters
        ----------
        connection: psycopg2.extras.NamedTupleCursor
            experiment-specific database connection created via
            :class:`ExperimentConnection <tmlib.models.utils.ExperimentConnection>`
        mapobject_id: int
            ID of parent
            :class:`Mapobject <tmlib.models.mapobject.Mapobject>`
        segmentation_layer_id: int
            ID of parent
            :class:`SegmentationLayer <tmlib.models.layer.SegmentationLayer>`
        polygon: shapely.geometry.polygon, optional
            outline of the segmented object
        centroid: shapely.geometry.point, optional
            centroid of the segmented object
        label: int, optional
            label assigned to the segmented object

        Raises
        ------
        ValueError
            when neither `polygon` nor `centroid` is provided

        Note
        ----
        The `centroid` is required, but it can be caluculate from the `polygon`.
        '''
        if polygon is None and centroid is None:
            raise ValueError('A mapobject segmentation must have a "centroid".')
        if centroid is None:
            geom_centroid = polygon.centroid.wkt
            geom_polygon = polygon.wkt
        else:
            geom_centroid = centroid.wkt
            geom_polygon = None
        connection.execute('''
            INSERT INTO mapobject_segmentations (
                mapobject_id, segmentation_layer_id,
                geom_polygon, geom_centroid, label
            )
            VALUES (
                %(mapobject_id)s, %(segmentation_layer_id)s,
                %(geom_polygon)s, %(geom_centroid)s, %(label)s
            );
        ''', {
            'mapobject_id': mapobject_id,
            'segmentation_layer_id': segmentation_layer_id,
            'geom_polygon': geom_polygon, 'geom_centroid': geom_centroid,
            'label': label
        })

    def __repr__(self):
        return '<%s(id=%d, mapobject_id=%r, segmentation_layer_id=%s)>' % (
            self.__class__.__name__, self.id, self.mapobject_id,
            self.segmentation_layer_id
        )


class SegmentationLayer(ExperimentModel):

    __tablename__ = 'segmentation_layers'

    __table_args__ = (
        UniqueConstraint('tpoint', 'zplane', 'mapobject_type_id'),
    )

    #: int: zero-based index in time series
    tpoint = Column(Integer, index=True)

    #: int: zero-based index in z stack
    zplane = Column(Integer, index=True)

    #: int: zoom level threshold below which polygons will not be visualized
    polygon_thresh = Column(Integer)

    #: int: zoom level threshold below which centroids will not be visualized
    centroid_thresh = Column(Integer)

    #: int: ID of parent channel
    mapobject_type_id = Column(
        Integer,
        ForeignKey('mapobject_types.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    #: tmlib.models.mapobject.MapobjectType: parent mapobject type
    mapobject_type = relationship(
        'MapobjectType',
        backref=backref('layers', cascade='all, delete-orphan'),
    )

    def __init__(self, mapobject_type_id, tpoint=None, zplane=None):
        '''
        Parameters
        ----------
        mapobject_type_id: int
            ID of parent
            :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`
        tpoint: int, optional
            zero-based time point index
        zplane: int, optional
            zero-based z-resolution index
        '''
        self.tpoint = tpoint
        self.zplane = zplane
        self.mapobject_type_id = mapobject_type_id

    @classmethod
    def get_tile_bounding_box(cls, x, y, z, maxzoom):
        '''Calculates the bounding box of a layer tile.

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
        '''
        # The extent of a tile of the current zoom level in mapobject
        # coordinates (i.e. coordinates on the highest zoom level)
        size = 256 * 2 ** (maxzoom - z)
        # Coordinates of the top-left corner of the tile
        x0 = x * size
        y0 = y * size
        # Coordinates with which to specify all corners of the tile
        # NOTE: y-axis is inverted!
        minx = x0
        maxx = x0 + size
        miny = -y0
        maxy = -y0 - size
        return (minx, miny, maxx, maxy)

    def calculate_zoom_thresholds(self, maxzoom_level):
        '''Calculates the zoom level below which mapobjects are
        represented on the map as centroids rather than polygons and the
        zoom level below which mapobjects are no longer visualized at all.
        These thresholds are necessary, because it would result in too much
        network traffic and the client would be overwhelmed by the large number
        of objects.

        Parameters
        ----------
        maxzoom_level: int
            maximum zoom level of the pyramid

        Returns
        -------
        Tuple[int]
            threshold zoom levels for visualization of polygons and centroids

        Note
        ----
        The optimal threshold levels depend on the number of points on the
        contour of objects, but also the size of the browser window and the
        resolution settings of the browser.
        '''
        # TODO: This is too simplistic. Calculate optimal zoom level by
        # sampling mapobjects at the highest resolution level and approximate
        # number of points that would be sent to the client.
        if self.mapobject_type.ref_type is None:
            polygon_thresh = 0
            centroid_thresh = 0
        else:
            polygon_thresh = maxzoom_level - 4
            polygon_thresh = 0 if polygon_thresh < 0 else polygon_thresh
            centroid_thresh = polygon_thresh - 2
            centroid_thresh = 0 if centroid_thresh < 0 else centroid_thresh
        return (polygon_thresh, centroid_thresh)

    def get_segmentations(self, x, y, z, tolerance=2):
        '''Get outlines of each
        :class:`Mapobject <tmlib.models.mapobject.Mapobject>`
        contained by a given pyramid tile.

        Parameters
        ----------
        x: int
            zero-based column map coordinate at the given `z` level
        y: int
            zero-based row map coordinate at the given `z` level
            (negative integer values due to inverted *y*-axis)
        z: int
            zero-based zoom level index
        tolerance: int, optional
            maximum distance in pixels between points on the contour of
            original polygons and simplified polygons;
            the higher the `tolerance` the less coordinates will be used to
            describe the polygon and the less accurate it will be
            approximated and; if ``0`` the original polygon is used
            (default: ``2``)

        Returns
        -------
        List[Tuple[int, str]]
            GeoJSON representation of each selected mapobject

        Note
        ----
        If *z* > `polygon_thresh` mapobjects are represented by polygons, if
        `polygon_thresh` < *z* < `centroid_thresh`,
        mapobjects are represented by points and if *z* < `centroid_thresh`
        they are not represented at all.
        '''
        logger.debug('get mapobject outlines falling into tile')
        session = Session.object_session(self)

        maxzoom = self.mapobject_type.experiment.pyramid_depth - 1
        minx, miny, maxx, maxy = self.get_tile_bounding_box(x, y, z, maxzoom)
        tile = (
            'POLYGON(('
                '{maxx} {maxy}, {minx} {maxy}, {minx} {miny}, {maxx} {miny}, '
                '{maxx} {maxy}'
            '))'.format(minx=minx, maxx=maxx, miny=miny, maxy=maxy)
        )

        do_simplify = self.centroid_thresh <= z < self.polygon_thresh
        do_nothing = z < self.centroid_thresh
        if do_nothing:
            logger.debug('dont\'t represent objects')
            return list()
        elif do_simplify:
            logger.debug('represent objects by centroids')
            query = session.query(
                MapobjectSegmentation.mapobject_id,
                MapobjectSegmentation.geom_centroid.ST_AsGeoJSON()
            )
            outlines = query.filter(
                MapobjectSegmentation.segmentation_layer_id == self.id,
                MapobjectSegmentation.geom_centroid.ST_Intersects(tile)
            ).\
            all()
        else:
            logger.debug('represent objects by polygons')
            tolerance = (maxzoom - z) ** 2 + 1
            logger.debug('simplify polygons using tolerance %d', tolerance)
            query = session.query(
                MapobjectSegmentation.mapobject_id,
                MapobjectSegmentation.geom_polygon.
                ST_SimplifyPreserveTopology(tolerance).ST_AsGeoJSON()
            )
            outlines = query.filter(
                MapobjectSegmentation.segmentation_layer_id == self.id,
                MapobjectSegmentation.geom_polygon.ST_Intersects(tile)
            ).\
            all()

        if len(outlines) == 0:
            logger.warn(
                'no outlines found for objects of type "%s" within tile: '
                'x=%d, y=%d, z=%d', self.mapobject_type.name, x, y, z
            )

        return outlines

    def __repr__(self):
        return (
            '<%s(id=%d, mapobject_type_id=%r)>'
            % (self.__class__.__name__, self.id, self.mapobject_type_id)
        )

