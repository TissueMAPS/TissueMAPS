# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016-2019 University of Zurich.
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
import logging
import csv
from cStringIO import StringIO
from sqlalchemy import (
    Column, String, Integer, BigInteger, ForeignKey, Boolean, Index,
    PrimaryKeyConstraint, UniqueConstraint, ForeignKeyConstraint
)
from sqlalchemy.dialects.postgresql import HSTORE
from sqlalchemy.orm import relationship, backref

from tmlib.models.base import (
    ExperimentModel, DistributedExperimentModel, IdMixIn
)
from tmlib import cfg

logger = logging.getLogger(__name__)


class Feature(ExperimentModel, IdMixIn):

    '''A *feature* is a measurement that is associated with a particular
    :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`.
    For example a *feature* named "Morphology_Area"
    would correspond to values reflecting the area of each
    individual :class:`Mapobject <tmlib.models.mapobject.Mapobject>`.

    '''

    __tablename__ = 'features'

    __table_args__ = (UniqueConstraint('name', 'mapobject_type_id'), )

    #: str: name given to the feature
    name = Column(String, index=True)

    #: bool: whether the feature is an aggregate of child object features
    is_aggregate = Column(Boolean, index=True)

    #: int: id of the parent mapobject type
    mapobject_type_id = Column(
        Integer,
        ForeignKey('mapobject_types.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    #: tmlib.models.mapobject.MapobjectType: parent mapobject type
    mapobject_type = relationship(
        'MapobjectType',
        backref=backref('features', cascade='all, delete-orphan')
    )

    def __init__(self, name, mapobject_type_id, is_aggregate=False):
        '''
        Parameters
        ----------
        name: str
            name of the feature
        mapobject_type_id: int
            ID of parent
            :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`
        is_aggregate: bool, optional
            whether the feature is an aggregate calculated based on another
            feature
        '''
        self.name = name
        self.mapobject_type_id = mapobject_type_id
        self.is_aggregate = is_aggregate

    def __repr__(self):
        return '<Feature(id=%r, name=%r)>' % (self.id, self.name)


class FeatureValues(DistributedExperimentModel):

    '''An individual value of a :class:`Feature <tmlib.models.feature.Feature>`
    that was extracted for a given
    :class:`Mapobject <tmlib.models.mapobject.Mapobject>`.
    '''

    __tablename__ = 'feature_values'

    __table_args__ = (
        PrimaryKeyConstraint('partition_key', 'mapobject_id', 'tpoint'),
        ForeignKeyConstraint(
            ['mapobject_id', 'partition_key'],
            ['mapobjects.id', 'mapobjects.partition_key'],
            ondelete='CASCADE'
        )
    )

    __distribute_by__ = 'partition_key'

    __distribution_method__ = 'hash'

    __colocate_with__ = 'mapobjects'

    partition_key = Column(Integer, index=True, nullable=False)

    #: Dict[str, str]: mapping of feature ID to value encoded as text
    # NOTE: HSTORE is more performant than JSONB upon SELECT and upon INSERT.
    # However, it only supports TEXT, such that values would need to be casted
    # when loaded into Python. One could define a custom type for this purpose.
    values = Column(HSTORE)

    #: int: zero-based time point index
    tpoint = Column(Integer, index=True)

    #: int: ID of the parent mapobject
    mapobject_id = Column(BigInteger, index=True)

    def __init__(self, partition_key, mapobject_id, values, tpoint=None):
        '''
        Parameters
        ----------
        partition_key: int
            key that determines on which shard the object will be stored
        mapobject_id: int
            ID of the mapobject to which values should be assigned
        values: Dict[str, float]
            mapping of feature ID to value
        tpoint: int, optional
            zero-based time point index
        '''
        self.partition_key = partition_key
        self.mapobject_id = mapobject_id
        self.tpoint = tpoint
        self.values = values

    @classmethod
    def _add(cls, connection, instance):
        if not isinstance(instance, FeatureValues):
            raise TypeError(
                'Object must have type tmlib.models.feature.FeatureValues'
            )
        connection.execute('''
            INSERT INTO feature_values AS v (
                parition_key, values, mapobject_id, tpoint
            )
            VALUES (
                %(partition_key)s, %(values)s, %(mapobject_id)s, %(tpoint)s
            )
            ON CONFLICT
            ON CONSTRAINT feature_values_mapobject_id_tpoint_key
            DO UPDATE
            SET values = v.values || %(values)s
            WHERE v.mapobject_id = %(mapobject_id)s
            AND v.tpoint = %(tpoint)s
        ''', {
            'partition_key': instance.partition_key,
            'values': instance.values,
            'mapobject_id': instance.mapobject_id,
            'tpoint': instance.tpoint
        })

    @classmethod
    def _bulk_ingest(cls, connection, instances):
        f = StringIO()
        w = csv.writer(f, delimiter=';')
        for obj in instances:
            w.writerow((
                obj.partition_key, obj.mapobject_id, obj.tpoint,
                ','.join([
                    '=>'.join([k, str(v)]) for k, v in obj.values.iteritems()
                ])
            ))
        columns = ('partition_key', 'mapobject_id', 'tpoint', 'values')
        f.seek(0)
        connection.copy_from(
            f, cls.__table__.name, sep=';', columns=columns, null=''
        )
        f.close()

    def __repr__(self):
        return (
            '<FeatureValues(id=%r, tpoint=%r, mapobject_id=%r)>'
            % (self.id, self.tpoint, self.mapobject_id)
        )
