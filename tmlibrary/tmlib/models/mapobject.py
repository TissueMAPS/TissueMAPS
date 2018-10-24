# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016-2018 University of Zurich.
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
import csv
import logging
import random
import collections
import pandas as pd
from cStringIO import StringIO
from sqlalchemy import func, case
from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape
from sqlalchemy.orm import Session
from sqlalchemy import (
    Column, String, Integer, BigInteger, Boolean, ForeignKey, not_, Index,
    UniqueConstraint, PrimaryKeyConstraint, ForeignKeyConstraint
)
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property

from tmlib import cfg
from tmlib.models.dialect import _compile_distributed_query
from tmlib.models.result import ToolResult, LabelValues
from tmlib.models.base import (
    ExperimentModel, DistributedExperimentModel, DateMixIn, IdMixIn
)
from tmlib.models.feature import Feature, FeatureValues
from tmlib.models.types import ST_GeomFromText, ST_SimplifyPreserveTopology
from tmlib.models.site import Site
from tmlib.utils import autocreate_directory_property, create_partitions

logger = logging.getLogger(__name__)


class MapobjectType(ExperimentModel, IdMixIn):

    '''A *mapobject type* represents a conceptual group of *mapobjects*
    (segmented objects) that reflect different biological entities,
    such as "cells" or "nuclei" for example.

    Attributes
    ----------
    records: List[tmlib.models.result.ToolResult]
        records belonging to the mapobject type
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
    def delete_cascade(cls, connection, static=None):
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
        connection: tmlib.models.utils.ExperimentConnection
            experiment-specific database connection
        static: bool, optional
            if ``True`` static types ("Plates", "Wells", "Sites") will be
            deleted, if ``False`` non-static types will be delted, if ``None``
            all types will be deleted (default: ``None``)

        '''
        ids = list()
        if static is not None:
            if static:
                logger.debug('delete static mapobjects')
                connection.execute('''
                    SELECT id FROM mapobject_types
                    WHERE name IN ('Plates', 'Wells', 'Sites')
                ''')
            else:
                logger.debug('delete static mapobjects')
                connection.execute('''
                    SELECT id FROM mapobject_types
                    WHERE name NOT IN ('Plates', 'Wells', 'Sites')
                ''')
        else:
            connection.execute('''
                    SELECT id FROM mapobject_types
            ''')
        records = connection.fetchall()
        ids.extend([r.id for r in records])

        for id in ids:
            logger.debug('delete mapobjects of type %d', id)
            Mapobject.delete_cascade(connection, id)
            logger.debug('delete mapobject type %d', id)
            connection.execute('''
                DELETE FROM mapobject_types WHERE id = %(id)s;
            ''', {
                'id': id
            })

    def get_site_geometry(self, site_id):
        '''Gets the geometric representation of a
        :class:`Site <tmlib.models.site.Site>`.
        in form of a
        :class:`MapobjectSegmentation <tmlib.models.mapobject.MapobjectSegmentation>`.

        Parameters
        ----------
        site_id: int
            ID of the :class:`Site <tmlib.models.site.Site>`

        Returns
        -------
        geoalchemy2.elements.WKBElement
        '''
        session = Session.object_session(self)
        mapobject_type = session.query(MapobjectType.id).\
            filter_by(ref_type=Site.__name__).\
            one()
        segmentation = session.query(MapobjectSegmentation.geom_polygon).\
            join(Mapobject).\
            filter(
                Mapobject.partition_key == site_id,
                Mapobject.mapobject_type_id == mapobject_type.id
            ).\
            one()
        return segmentation.geom_polygon

    def get_segmentations_per_site(self, site_id, tpoint, zplane,
             as_polygons=True):
        '''Gets each
        :class:`MapobjectSegmentation <tmlib.models.mapobject.MapobjectSegmentation>`
        that intersects with the geometric representation of a given
        :class:`Site <tmlib.models.site.Site>`.

        Parameters
        ----------
        site_id: int
            ID of a :class:`Site <tmlib.models.site.Site>` for which
            objects should be spatially filtered
        tpoint: int
            time point for which objects should be filtered
        zplane: int
            z-plane for which objects should be filtered
        as_polygons: bool, optional
            whether segmentations should be returned as polygons;
            if ``False`` segmentations will be returned as centroid points
            (default: ``True``)

        Returns
        -------
        Tuple[Union[int, geoalchemy2.elements.WKBElement]]
            label and geometry for each segmented object
        '''
        session = Session.object_session(self)

        layer = session.query(SegmentationLayer.id).\
            filter_by(mapobject_type_id=self.id, tpoint=tpoint, zplane=zplane).\
            one()

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
            filter_by(segmentation_layer_id=layer.id, partition_key=site_id).\
            order_by(MapobjectSegmentation.mapobject_id).\
            all()

        return segmentations

    def get_feature_values_per_site(self, site_id, tpoint, feature_ids=None):
        '''Gets all
        :class:`FeatureValues <tmlib.models.feature.FeatureValues>`
        for each :class:`Mapobject <tmlib.models.MapobjectSegmentation>`
        where the corresponding
        :class:`MapobjectSegmentation <tmlib.models.mapobject.MapobjectSegmentation>`
        intersects with the geometric representation of a given
        :class:`Site <tmlib.models.site.Site>`.

        Parameters
        ----------
        site_id: int
            ID of a :class:`Site <tmlib.models.site.Site>` for which
            objects should be spatially filtered
        tpoint: int
            time point for which objects should be filtered
        feature_ids: List[int], optional
            ID of each :class:`Feature <tmlib.models.feature.Feature>` for
            which values should be selected; by default all features will be
            selected

        Returns
        -------
        pandas.DataFrame[numpy.float]
            feature values for each mapobject
        '''
        session = Session.object_session(self)

        features = session.query(Feature.id, Feature.name).\
            filter_by(mapobject_type_id=self.id)
        if feature_ids is not None:
            features = features.filter(Feature.id.in_(feature_ids))
        features = features.all()
        feature_map = {str(id): name for id, name in features}

        if feature_ids is not None:
            records = session.query(
                FeatureValues.mapobject_id,
                FeatureValues.values.slice(feature_map.keys()).label('values')
            )
        else:
            records = session.query(
                FeatureValues.mapobject_id,
                FeatureValues.values
            )
        records = records.\
            join(Mapobject).\
            join(MapobjectSegmentation).\
            filter(
                Mapobject.mapobject_type_id == self.id,
                FeatureValues.tpoint == tpoint,
                FeatureValues.partition_key == site_id
            ).\
            order_by(Mapobject.id).\
            all()
        values = [r.values for r in records]
        mapobject_ids = [r.mapobject_id for r in records]
        df = pd.DataFrame(values, index=mapobject_ids)
        df.rename(columns=feature_map, inplace=True)

        return df

    def get_label_values_per_site(self, site_id, tpoint):
        '''Gets all :class:`LabelValues <tmlib.models.result.LabelValues>`
        for each :class:`Mapobject <tmlib.models.MapobjectSegmentation>`
        where the corresponding
        :class:`MapobjectSegmentation <tmlib.models.mapobject.MapobjectSegmentation>`
        intersects with the geometric representation of a given
        :class:`Site <tmlib.models.site.Site>`.

        Parameters
        ----------
        site_id: int
            ID of a :class:`Site <tmlib.models.site.Site>` for which
            objects should be spatially filtered
        tpoint: int, optional
            time point for which objects should be filtered

        Returns
        -------
        pandas.DataFrame[numpy.float]
            label values for each mapobject
        '''
        session = Session.object_session(self)

        labels = session.query(ToolResult.id, ToolResult.name).\
            filter_by(mapobject_type_id=self.id).\
            all()
        label_map = {str(id): name for id, name in labels}

        records = session.query(
                LabelValues.mapobject_id, LabelValues.values
            ).\
            join(Mapobject).\
            join(MapobjectSegmentation).\
            filter(
                Mapobject.mapobject_type_id == self.id,
                LabelValues.tpoint == tpoint,
                LabelValues.partition_key == site_id
            ).\
            order_by(Mapobject.id).\
            all()
        values = [r.values for r in records]
        mapobject_ids = [r.mapobject_id for r in records]
        df = pd.DataFrame(values, index=mapobject_ids)
        df.rename(columns=label_map, inplace=True)

        return df

    def identify_border_objects_per_site(self, site_id, tpoint, zplane):
        '''Determines for each :class:`Mapobject <tmlib.models.MapobjectSegmentation>`
        where the corresponding
        :class:`MapobjectSegmentation <tmlib.models.mapobject.MapobjectSegmentation>`
        intersects with the geometric representation of a given
        :class:`Site <tmlib.models.site.Site>`, whether the objects is touches
        at the border of the site.

        Parameters
        ----------
        site_id: int
            ID of a :class:`Site <tmlib.models.site.Site>` for which
            objects should be spatially filtered
        tpoint: int
            time point for which objects should be filtered
        zplane: int
            z-plane for which objects should be filtered

        Returns
        -------
        pandas.Series[numpy.bool]
            ``True`` if the mapobject touches the border of the site and
            ``False`` otherwise
        '''
        session = Session.object_session(self)
        site_geometry = self.get_site_geometry(site_id)

        layer = session.query(SegmentationLayer.id).\
            filter_by(mapobject_type_id=self.id, tpoint=tpoint, zplane=zplane).\
            one()

        records = session.query(
                MapobjectSegmentation.mapobject_id,
                case([(
                    MapobjectSegmentation.geom_polygon.ST_Intersects(
                        site_geometry.ST_Boundary()
                    )
                    , True
                )], else_=False).label('is_border')
            ).\
            filter(
                MapobjectSegmentation.segmentation_layer_id == layer.id,
                MapobjectSegmentation.partition_key == site_id
            ).\
            order_by(MapobjectSegmentation.mapobject_id).\
            all()
        values = [r.is_border for r in records]
        mapobject_ids = [r.mapobject_id for r in records]
        s = pd.Series(values, index=mapobject_ids)

        return s

    def __repr__(self):
        return '<MapobjectType(id=%d, name=%r)>' % (self.id, self.name)


class Mapobject(DistributedExperimentModel):

    '''A *mapobject* represents a connected pixel component in an
    image. It has one or more 2D segmentations that can be used to represent
    the object on the map and may also be associated with measurements
    (*features*), which can be queried or used for further analysis.
    '''

    #: str: name of the corresponding database table
    __tablename__ = 'mapobjects'

    __table_args__ = (
        PrimaryKeyConstraint('id', 'partition_key'),
    )

    __distribute_by__ = 'partition_key'

    __distribution_method__ = 'hash'

    partition_key = Column(Integer, nullable=False)

    id = Column(BigInteger, unique=True, autoincrement=True)

    #: int: ID of another record to which the object is related.
    #: This could refer to another mapobject in the same table, e.g. in order
    #: to track proliferating cells, or a record in another reference table,
    #: e.g. to identify the corresponding record of a "Well".
    ref_id = Column(BigInteger, index=True)

    #: int: ID of parent mapobject type
    mapobject_type_id = Column(Integer, index=True, nullable=False)

    def __init__(self, partition_key, mapobject_type_id, ref_id=None):
        '''
        Parameters
        ----------
        partition_key: int
            key that determines on which shard the object will be stored
        mapobject_type_id: int
            ID of parent
            :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`
        ref_id: int, optional
            ID of the referenced record

        See also
        --------
        :attr:`tmlib.models.mapobject.MapobjectType.ref_type`
        '''
        self.partition_key = partition_key
        self.mapobject_type_id = mapobject_type_id
        self.ref_id = ref_id

    @classmethod
    def _delete_cascade(cls, connection, mapobject_ids):
        logger.debug('delete mapobjects')
        # NOTE: Using ANY with an ARRAY is more performant than using IN.
        # TODO: Ideally we would like to join with mapobject_types.
        # However, at the moment there seems to be no way to DELETE entries
        # from a distributed table with a complex WHERE clause.
        # If the number of objects is too large this will lead to issues.
        # Therefore, we delete rows in batches.
        mapobject_id_partitions = create_partitions(mapobject_ids, 100000)
        # This will DELETE all records of referenced tables as well.
        # FIXME: How to cast to correct BigInteger type in $$ escaped query?
        sql = '''
             DELETE FROM mapobjects
             WHERE id = ANY(%(mapobject_ids)s)
        '''
        for mids in mapobject_id_partitions:
            connection.execute(
                _compile_distributed_query(sql), {'mapobject_ids': mids}
            )

    @classmethod
    def delete_objects_with_invalid_segmentation(cls, connection):
        '''Deletes all instances with invalid segmentations as well as all
        "children" instances of
        :class:`MapobjectSegmentation <tmlib.models.mapobject.MapobjectSegmentation>`
        :class:`FeatureValues <tmlib.models.feature.FeatureValues>`,
        :class:`LabelValues <tmlib.models.feature.LabelValues>`.

        Parameters
        ----------
        connection: tmlib.models.utils.ExperimentConnection
            experiment-specific database connection

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
    def delete_objects_with_missing_segmentations(cls, connection):
        '''Deletes all instances that don't have a
        :class:`MapobjectSegmentation <tmlib.models.mapobject.MapobjectSegmentation>`
        as well as their "children" instances of
        :class:`FeatureValues <tmlib.models.feature.FeatureValues>`
        and :class:`LabelValues <tmlib.models.feature.LabelValues>`.

        Parameters
        ----------
        connection: tmlib.models.utils.ExperimentConnection
            experiment-specific database connection

        '''
        connection.execute('''
            SELECT m.id FROM mapobjects m
            LEFT OUTER JOIN mapobject_segmentations s
            ON m.id = s.mapobject_id AND m.partition_key = s.partition_key
            WHERE s.mapobject_id IS NULL
        ''')
        mapobjects = connection.fetchall()
        missing_ids = [s.id for s in mapobjects]
        if missing_ids:
            logger.info(
                'delete %d mapobjects with missing segmentations',
                len(missing_ids)
            )
            cls._delete_cascade(connection, missing_ids)

    @classmethod
    def delete_objects_with_missing_feature_values(cls, connection):
        '''Deletes all instances that don't have
        :class:`FeatureValues <tmlib.models.feature.FeatureValues>`
        as well as their "children" instances of
        :class:`MapobjectSegmentation <tmlib.models.mapobject.MapobjectSegmentation>`
        and :class:`LabelValues <tmlib.models.feature.LabelValues>`.

        Parameters
        ----------
        connection: tmlib.models.utils.ExperimentConnection
            experiment-specific database connection

        '''
        # Make sure only mapobject types are selected that have any features,
        # otherwise all mapobjects of that type would be deleted.
        connection.execute('''
            SELECT m.mapobject_type_id, count(v.mapobject_id)
            FROM feature_values AS v
            JOIN mapobjects AS m
            ON m.id = v.mapobject_id AND m.partition_key = v.partition_key
            GROUP BY m.mapobject_type_id
        ''')
        results = connection.fetchall()
        missing_ids = []
        for mapobject_type_id, count in results:
            connection.execute('''
                SELECT m.id FROM mapobjects AS m
                LEFT OUTER JOIN feature_values AS v
                ON m.id = v.mapobject_id AND m.partition_key = v.partition_key
                WHERE m.mapobject_type_id = %(mapobject_type_id)s
                AND v.mapobject_id IS NULL
            ''', {
                'mapobject_type_id': mapobject_type_id
            })
            mapobjects = connection.fetchall()
            missing_ids.extend([s.id for s in mapobjects])

        if missing_ids:
            logger.info(
                'delete %d mapobjects of type %d with missing feature '
                'values', len(missing_ids), mapobject_type_id
            )
            cls._delete_cascade(connection, missing_ids)

    @classmethod
    def _add(cls, connection, instance):
        if not isinstance(instance, cls):
            raise TypeError('Object must have type %s' % cls.__name__)
        instance.id = cls.get_unique_ids(connection, 1)[0]
        connection.execute('''
            INSERT INTO mapobjects (
                partition_key, id, mapobject_type_id, ref_id
            )
            VALUES (
                %(partition_key)s, %(id)s, %(mapobject_type_id)s, %(ref_id)s
            )
        ''', {
            'id': instance.id,
            'partition_key': instance.partition_key,
            'mapobject_type_id': instance.mapobject_type_id,
            'ref_id': instance.ref_id
        })
        return instance

    @classmethod
    def _bulk_ingest(cls, connection, instances):
        if not instances:
            return []
        f = StringIO()
        w = csv.writer(f, delimiter=';')
        ids = cls.get_unique_ids(connection, len(instances))
        for i, obj in enumerate(instances):
            if not isinstance(obj, cls):
                raise TypeError('Object must have type %s' % cls.__name__)
            obj.id = ids[i]
            w.writerow((
                obj.partition_key, obj.id, obj.mapobject_type_id, obj.ref_id
            ))
        columns = ('partition_key', 'id', 'mapobject_type_id', 'ref_id')
        f.seek(0)
        connection.copy_from(
            f, cls.__table__.name, sep=';', columns=columns, null=''
        )
        f.close()
        return instances

    def __repr__(self):
        return '<%s(id=%r, mapobject_type_id=%r)>' % (
            self.__class__.__name__, self.id, self.mapobject_type_id
        )


class MapobjectSegmentation(DistributedExperimentModel):

    '''A *segmentation* provides the geometric representation
    of a :class:`Mapobject <tmlib.models.mapobject.Mapobject>`.
    '''

    __tablename__ = 'mapobject_segmentations'

    __table_args__ = (
        PrimaryKeyConstraint(
            'mapobject_id', 'partition_key', 'segmentation_layer_id'
        ),
        ForeignKeyConstraint(
            ['mapobject_id', 'partition_key'],
            ['mapobjects.id', 'mapobjects.partition_key'],
            ondelete='CASCADE'
        )
    )

    __distribution_method__ = 'hash'

    __distribute_by__ = 'partition_key'

    __colocate_with__ = 'mapobjects'

    partition_key = Column(Integer, nullable=False)

    #: str: EWKT POLYGON geometry
    geom_polygon = Column(Geometry('POLYGON'))

    #: str: EWKT POINT geometry
    geom_centroid = Column(Geometry('POINT'), nullable=False)

    #: int: label assigned to the object upon segmentation
    label = Column(Integer, index=True)

    #: int: ID of parent mapobject
    mapobject_id = Column(BigInteger)

    #: int: ID of parent segmentation layer
    segmentation_layer_id = Column(Integer)

    def __init__(self, partition_key, geom_polygon, geom_centroid, mapobject_id,
            segmentation_layer_id, label=None):
        '''
        Parameters
        ----------
        partition_key: int
            key that determines on which shard the object will be stored
        geom_polygon: shapely.geometry.polygon.Polygon
            polygon geometry of the mapobject contour
        geom_centroid: shapely.geometry.point.Point
            point geometry of the mapobject centroid
        mapobject_id: int
            ID of parent :class:`Mapobject <tmlib.models.mapobject.Mapobject>`
        segmentation_layer_id: int
            ID of parent
            :class:`SegmentationLayer <tmlib.models.layer.SegmentationLayer>`
        label: int, optional
            label assigned to the segmented object
        '''
        self.partition_key = partition_key
        self.geom_polygon = getattr(geom_polygon, 'wkt', None)
        self.geom_centroid = geom_centroid.wkt
        self.mapobject_id = mapobject_id
        self.segmentation_layer_id = segmentation_layer_id
        self.label = label

    @classmethod
    def _add(cls, connection, instance):
        if not isinstance(instance, cls):
            raise TypeError('Object must have type %s' % cls.__name__)
        connection.execute('''
            INSERT INTO mapobject_segmentations AS s (
                partition_key, mapobject_id, segmentation_layer_id,
                geom_polygon, geom_centroid, label
            )
            VALUES (
                %(partition_key)s, %(mapobject_id)s, %(segmentation_layer_id)s,
                %(geom_polygon)s, %(geom_centroid)s, %(label)s
            )
            ON CONFLICT
            ON CONSTRAINT mapobject_segmentations_pkey
            DO UPDATE
            SET geom_polygon = %(geom_polygon)s, geom_centroid = %(geom_centroid)s
            WHERE s.mapobject_id = %(mapobject_id)s
            AND s.partition_key = %(partition_key)s
            AND s.segmentation_layer_id = %(segmentation_layer_id)s
        ''', {
            'partition_key': instance.partition_key,
            'mapobject_id': instance.mapobject_id,
            'segmentation_layer_id': instance.segmentation_layer_id,
            'geom_polygon': instance.geom_polygon,
            'geom_centroid': instance.geom_centroid,
            'label': instance.label
        })

    @classmethod
    def _bulk_ingest(cls, connection, instances):
        if not instances:
            return
        f = StringIO()
        w = csv.writer(f, delimiter=';')
        for obj in instances:
            if not isinstance(obj, cls):
                raise TypeError('Object must have type %s' % cls.__name__)
            w.writerow((
                obj.partition_key,
                obj.geom_polygon,
                obj.geom_centroid,
                obj.mapobject_id, obj.segmentation_layer_id, obj.label
            ))
        columns = (
            'partition_key', 'geom_polygon', 'geom_centroid', 'mapobject_id',
            'segmentation_layer_id', 'label'
        )
        f.seek(0)
        connection.copy_from(
            f, cls.__table__.name, sep=';', columns=columns, null=''
        )
        f.close()

    def __repr__(self):
        return '<%s(id=%r, mapobject_id=%r, segmentation_layer_id=%r)>' % (
            self.__class__.__name__, self.id, self.mapobject_id,
            self.segmentation_layer_id
        )


class SegmentationLayer(ExperimentModel, IdMixIn):

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

    def calculate_zoom_thresholds(self, maxzoom_level, represent_as_polygons):
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
        represent_as_polygons: bool
            whether the objects should be represented as polygons or only as
            centroid points

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
        # TODO: This is a bit too simplistic. Ideally, we would calculate
        # the optimal zoom level by sampling mapobjects at the highest
        # resolution level and approximate number of points that would be sent
        # to the client. This is tricky, however, because the current view
        # and thus the number of requested mapobject segmentations dependents
        # on the size of monitor.
        if self.tpoint is None and self.zplane is None:
            if self.mapobject_type.ref_type == 'Plate':
                polygon_thresh = 0
                centroid_thresh = 0
            elif self.mapobject_type.ref_type == 'Well':
                polygon_thresh = maxzoom_level - 11
                centroid_thresh = 0
            elif self.mapobject_type.ref_type == 'Site':
                polygon_thresh = maxzoom_level - 8
                centroid_thresh = 0
        else:
            if represent_as_polygons:
                polygon_thresh = maxzoom_level - 4
            else:
                polygon_thresh = maxzoom_level + 1
            centroid_thresh = polygon_thresh - 2

        polygon_thresh = 0 if polygon_thresh < 0 else polygon_thresh
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
            "POLYGON(("
                "{maxx} {maxy}, "
                "{minx} {maxy}, "
                "{minx} {miny}, "
                "{maxx} {miny}, "
                "{maxx} {maxy}"
            "))"
            .format(minx=minx, maxx=maxx, miny=miny, maxy=maxy)
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
                MapobjectSegmentation.geom_centroid.ST_Intersects(ST_GeomFromText(tile))
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
