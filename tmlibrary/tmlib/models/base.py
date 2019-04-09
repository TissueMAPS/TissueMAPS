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
'''Abstract base and mixin classes for database models.

Mixin classes must implement additional table columns using the
`declared_attr <http://docs.sqlalchemy.org/en/latest/orm/extensions/declarative/api.html#sqlalchemy.ext.declarative.declared_attr>`_
decorator.

'''
import os
import logging
import sqlalchemy
from sqlalchemy.ext.declarative import (
    declarative_base, DeclarativeMeta, declared_attr
)
from sqlalchemy import Column, DateTime, Integer, BigInteger, String
from sqlalchemy import func
from sqlalchemy.schema import DropTable, CreateTable
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.dialects import registry
from abc import ABCMeta
from abc import abstractmethod
from abc import abstractproperty

from tmlib import utils

logger = logging.getLogger(__name__)


class _DeclarativeABCMeta(DeclarativeMeta, ABCMeta):

    '''Metaclass for declarative base classes.'''

    def __init__(self, name, bases, d):
        DeclarativeMeta.__init__(self, name, bases, d)
        if not hasattr(self, '__table__'):
            return
        distribution_method = d.pop('__distribution_method__', None)
        distribution_column = (
            d.pop('__distribute_by__', None) or
            getattr(self, '__bind_key__', None)
        )
        colocated_table = d.pop('__colocate_with__', None)
        if distribution_method is not None:
            self.__table__.info['is_distributed'] = True
            self.__table__.info['distribution_method'] = distribution_method
            if distribution_method in {'range', 'hash'}:
                if distribution_column is None:
                    raise ValueError(
                        'Table "%s" is distributed by "%s" and must therefore '
                        'provide a distribution column via "__distribute_by__".'
                        % (self.__table__.name, distribution_method)
                    )
                column_type = self.__table__.c[distribution_column].type
                if not isinstance(column_type, sqlalchemy.types.Integer):
                    raise TypeError(
                        'Distribution column "%s" of table "%s" must have type '
                        '"%s" for distribtion method "%s"' % (
                            distribution_column, self.__table__.name,
                            sqlalchemy.types.Integer.__name__,
                            table.info['distribution_method']
                        )
                    )
                columns = self.__table__.c
                if distribution_column not in columns:
                    raise ValueError(
                        'Specified distribution column "%s" '
                        'is not a column of table "%s".'
                        % (distribution_column, self.__table__.name)
                    )
                self.__table__.info['distribute_by'] = distribution_column
                self.__table__.info['colocate_with'] = colocated_table
            elif distribution_method == 'replication':
                self.__table__.info['distribute_by'] = None
                self.__table__.info['colocate_with'] = None
            else:
                raise ValueError(
                    'Table "%s" specified an unsupported distribution method. '
                    'Supported are: "range", "hash" and "replication".'
                    % self.__table__.name
                )
        else:
            self.__table__.info['is_distributed'] = False


#: Abstract base class for models of the main database.
_MainBase = declarative_base(
    name='MainBase', metaclass=_DeclarativeABCMeta
)

#: Abstract base class for models of an experiment-specific database.
_ExperimentBase = declarative_base(
    name='ExperimentBase', metaclass=_DeclarativeABCMeta
)


class DateMixIn(object):

    '''Mixin class to automatically add columns with datetime stamps to a
    database table.
    '''

    # NOTE: We use the "declared_attr" property for the mixin to ensure that
    # the columns are added to the end of the columns list. This simplifies
    # table distribution.

    @declared_attr
    def created_at(cls):
        '''datetime: date and time when the row was inserted into the column'''
        return Column(DateTime, default=sqlalchemy.func.now())

    @declared_attr
    def updated_at(cls):
        '''datetime: date and time when the row was last updated'''
        # TODO: CREATE TRIGGER to update independent of ORM
        return Column(
            DateTime,
            default=sqlalchemy.func.now(), onupdate=sqlalchemy.func.now()
        )


class IdMixIn(object):

    '''Mixin class to automatically add an ID column to a database table
    with primary key constraint.
    '''

    id = Column(Integer, primary_key=True, autoincrement=True)

    @property
    def hash(self):
        '''str: encoded `id`'''
        return utils.encode_pk(self.id)


class MainModel(_MainBase, IdMixIn):

    '''Abstract base class for models of the main ("public") schema.'''

    __abstract__ = True


class ExperimentModel(_ExperimentBase):

    '''Abstract base class for models of an experiment-specific schema.'''

    __abstract__ = True


class DistributedExperimentModel(ExperimentModel):

    '''Abstract base class for models of an experiment-specific schema
    that is partitioned and potentially distributed over multiple database
    servers.

    Warning
    -------
    Distributed models cannot be modified within a transaction.
    '''

    __abstract__ = True

    @abstractmethod
    def _bulk_ingest(cls, connection, instances):
        '''Ingests multiple records in the database en bulk.

        Parameters
        ----------
        connection: tmlib.models.utils.ExperimentConnection
            experiment-specific database connection
        instances: List[tmlib.models.base.DistributedExperimentModel]
            instances of the derived class
        '''
        pass

    @abstractmethod
    def _add(cls, connection, instances):
        '''Adds one records in the database, i.e. either inserts the record
        or updates it in case it already exists.

        Parameters
        ----------
        connection: tmlib.models.utils.ExperimentConnection
            experiment-specific database connection
        instances: List[tmlib.models.base.DistributedExperimentModel]
            instances of the derived class
        '''
        pass

    @classmethod
    def get_unique_ids(cls, connection, n):
        '''Gets unique, shard-specific values for the distribution column.

        Parameters
        ----------
        connection: tmlib.models.utils.ExperimentConnection
            experiment-specific database connection
        n: int
            number of IDs that should be returned

        Returns
        -------
        List[int]
            unique, shard-specific IDs

        '''
        logger.debug(
            'get %d unique identifiers for distributed model "%s"',
            n, cls.__name__
        )
        connection.execute(
            'SELECT nextval(%(sequence)s) FROM generate_series(1, %(n)s);',
            {'sequence': '{t}_id_seq'.format(t=cls.__table__.name), 'n': n}
        )
        values = connection.fetchall()
        return [v[0] for v in values]


class FileSystemModel(ExperimentModel, IdMixIn):

    '''Abstract base class for model classes, which refer to data
    stored on disk outside of the database.
    '''

    __abstract__ = True

    _location = Column('location', String(4096))

    @abstractproperty
    def location(self):
        '''str: location on disk

        Devired classes must implement `location` and decorate it with
        :func:`sqlalchemy.ext.hybrid.hyprid_property`.
        '''
        pass

    @location.setter
    def location(self, value):
        self._location = value


class DirectoryModel(FileSystemModel):

    '''Abstract base class for model classes, which refer to data
    stored in directories on disk.
    '''

    __abstract__ = True


class FileModel(FileSystemModel):

    '''Abstract base class for model classes, which refer to data
    stored in files on disk.
    '''

    __abstract__ = True

    @property
    def format(self):
        '''str: file extension, e.g. ".tif" or ".jpg"'''
        return os.path.splitext(self.name)[1]

    @abstractmethod
    def get(self):
        '''Gets the file content.'''
        pass

    @abstractmethod
    def put(self, data):
        '''Puts `data` to the file.'''
        pass
