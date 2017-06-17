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
import logging
import csv
from cStringIO import StringIO
from sqlalchemy import (
    Column, String, Integer, BigInteger, ForeignKey, Boolean, Index,
    PrimaryKeyConstraint, UniqueConstraint, ForeignKeyConstraint
)
from sqlalchemy.dialects.postgresql import HSTORE
from sqlalchemy.orm import relationship, backref

from tmlib.models.base import ExperimentModel, IdMixIn
from tmlib.models.utils import ExperimentConnection
from tmlib.models.dialect import compile_distributed_query
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

    @classmethod
    def delete_cascade(cls, connection, mapobject_type_id=None, ids=[]):
        '''Deletes all instances for the given experiment as well as all
        referencing fields in
        :attr:`FeatureValues.values <tmlib.models.feature.FeatureValues.values>`.

        Parameters
        ----------
        connection: psycopg2.extras.NamedTupleCursor
            experiment-specific database connection created via
            :class:`ExperimentConnection <tmlib.models.utils.ExperimentConnection>`
        mapobject_type_id: int, optional
            ID of parent
            :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>` for
            which features should be deleted
        ids: List[int], optional
            IDs of features that should be deleted
        '''
        delete = True
        if mapobject_type_id:
            delete = False
            connection.execute('''
                SELECT id FROM features
                WHERE mapobject_type_id = %(mapobject_type_id)s
            ''', {
                'mapobject_type_id': mapobject_type_id
            })
            records = connection.fetchall()
            if records:
                delete = True
                ids = [r.id for r in records]
        if delete:
            logger.info('delete feature values')
            if ids:
                # TODO: Would it be worth indexing the HSTORE column?
                sql = '''
                    UPDATE feature_values
                    SET values = delete(values, %(feature_ids)s)
                '''
                connection.execute(
                    compile_distributed_query(sql),
                    {'feature_ids': map(str, ids)}
                )
                connection.execute('''
                    DELETE FROM features where id = ANY(%(feature_ids)s);
                ''', {
                    'feature_ids': ids
                })
            else:
                sql = "UPDATE feature_values SET values = $$' '$$;"
                connection.execute(compile_distributed_query(sql))
                connection.execute('DELETE FROM features;')

    def __repr__(self):
        return '<Feature(id=%r, name=%r)>' % (self.id, self.name)


class FeatureValues(ExperimentModel):

    '''An individual value of a :class:`Feature <tmlib.models.feature.Feature>`
    that was extracted for a given
    :class:`Mapobject <tmlib.models.mapobject.Mapobject>`.
    '''

    __tablename__ = 'feature_values'

    __table_args__ = (
        PrimaryKeyConstraint('mapobject_id', 'tpoint'),
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
    def add(cls, connection, feature_values):
        '''Adds object to the database table.

        Parameters
        ----------
        connection: psycopg2.extras.NamedTupleCursor
            experiment-specific database connection created via
            :class:`ExperimentConnection <tmlib.models.utils.ExperimentConnection>`
        feature_values: tmlib.models.feature.FeatureValues

        '''
        if not isinstance(feature_values, FeatureValues):
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
            'partition_key': feature_values.partition_key,
            'values': feature_values.values,
            'mapobject_id': feature_values.mapobject_id,
            'tpoint': feature_values.tpoint
        })

    @classmethod
    def add_multiple(cls, connection, feature_values):
        '''Adds multiple new records at once.

        Parameters
        ----------
        connection: psycopg2.extras.NamedTupleCursor
            experiment-specific database connection created via
            :class:`ExperimentConnection <tmlib.models.utils.ExperimentConnection>`
        feature_values: List[tmlib.models.feature.FeatureValues]
        '''
        f = StringIO()
        w = csv.writer(f, delimiter=';')
        for obj in feature_values:
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
