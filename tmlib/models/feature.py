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
    PrimaryKeyConstraint, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import HSTORE
from sqlalchemy.orm import relationship, backref

from tmlib.models.base import ExperimentModel
from tmlib.models.utils import ExperimentConnection
from tmlib.models.dialect import compile_distributed_query
from tmlib import cfg

logger = logging.getLogger(__name__)


class Feature(ExperimentModel):

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
    def delete_cascade(cls, connection, mapobject_type_ids=[], id=None):
        '''Deletes all instances for the given experiment as well as all
        referencing fields in
        :attr:`FeatureValues.values <tmlib.models.feature.FeatureValues.values>`.

        Parameters
        ----------
        connection: psycopg2.extras.NamedTupleCursor
            experiment-specific database connection created via
            :class:`ExperimentConnection <tmlib.models.utils.ExperimentConnection>`
        mapobject_type_ids: List[int], optional
            IDs of parent
            :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>` for
            which features should be deleted
        id: int, optional
            ID of a specific feature that should be deleted
        '''
        logger.info('delete feature values')
        if mapobject_type_ids:
            sql = '''
                UPDATE feature_values AS v SET values = hstore()
                FROM mapobjects AS m
                WHERE m.id = v.mapobject_id
                AND m.mapobject_type_id = ANY(%(mapobject_type_ids)s)
            '''
            connection.execute(
                compile_distributed_query(sql),
                {'mapobject_type_ids': mapobject_type_ids}
            )
            connection.execute(
                '''
                DELETE FROM features
                WHERE mapobject_type_id = ANY(%(mapobject_type_ids)s)
            ''', {
                'mapobject_type_ids': mapobject_type_ids
            })
        elif id is not None:
            sql = '''
                UPDATE feature_values SET values = delete(values, %(id)s);
            '''
            connection.execute(
                compile_distributed_query(sql),
                {'id': str(id)}
            )
            connection.execute('''
                DELETE FROM features where id = %(id)s;
            ''', {
                'id': id
            })
        else:
            sql = 'UPDATE feature_values SET values = hstore();'
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

    # TODO: We may want this to be a PRIMARY KEY CONTRAINT instead
    __table_args__ = (UniqueConstraint('mapobject_id', 'tpoint'), )

    __distribute_by_hash__ = 'mapobject_id'

    #: Dict[str, str]: mapping of feature ID to value encoded as text
    # NOTE: HSTORE is more performant than JSONB upon SELECT and upon INSERT.
    # However, it only supports TEXT, such that values would need to be casted
    # when loaded into Python. One could define a custom type for this purpose.
    values = Column(HSTORE)

    #: int: zero-based time point index
    tpoint = Column(Integer, index=True)

    #: int: ID of the parent mapobject (FOREIGN KEY)
    mapobject_id = Column(
        BigInteger,
        ForeignKey('mapobjects.id', ondelete='CASCADE'),
        index=True
    )

    def __init__(self, mapobject_id, values, tpoint=None):
        '''
        Parameters
        ----------
        mapobject_id: int
            ID of the mapobject to which values should be assigned
        values: Dict[str, float]
            mapping of feature ID to value
        tpoint: int, optional
            zero-based time point index
        '''
        self.mapobject_id = mapobject_id
        self.tpoint = tpoint
        self.values = values

    @classmethod
    def add(cls, connection, feature_values):
        '''Adds a new record.

        Parameters
        ----------
        connection: psycopg2.extras.NamedTupleCursor
            experiment-specific database connection created via
            :class:`ExperimentConnection <tmlib.models.utils.ExperimentConnection>`
        feature_values: tmlib.models.feature.FeatureValues
        '''
        connection.execute('''
            INSERT INTO feature_values AS v (values, mapobject_id, tpoint)
            VALUES (%(values)s, %(mapobject_id)s, %(tpoint)s)
            ON CONFLICT
            ON CONSTRAINT feature_values_mapobject_id_tpoint_key
            DO UPDATE
            SET values = v.values || %(values)s
            WHERE v.mapobject_id = %(mapobject_id)s
            AND v.tpoint = %(tpoint)s
        ''', {
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
                obj.mapobject_id, obj.tpoint,
                ','.join([
                    '=>'.join([k, str(v)]) for k, v in obj.values.iteritems()
                ])
            ))
        columns = ('mapobject_id', 'tpoint', 'values')
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
