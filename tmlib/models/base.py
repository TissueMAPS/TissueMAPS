# TmLibrary - TissueMAPS library for distibuted image processing routines.
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
'''Abstract base and mixin classes for database models.'''
import os
import logging
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta
from sqlalchemy import Column, DateTime, Integer, String
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


class DeclarativeABCMeta(DeclarativeMeta, ABCMeta):

    '''Metaclass for declarative base classes.'''

    def __init__(self, name, bases, d):
        distribute_by = (
            d.pop('__distribute_by_hash__', None) or
            getattr(self, '__bind_key__', None)
        )
        DeclarativeMeta.__init__(self, name, bases, d)
        if hasattr(self, '__table__'):
            if distribute_by is not None:
                column_names = [c.name for c in self.__table__.columns]
                if distribute_by not in column_names:
                    raise ValueError(
                        'Hash for PostgresXL distribution "%s" '
                        'is not a column of table "%s"'
                        % (distribute_by, self.__table__.name)
                    )
                self.__table__.info['distribute_by_hash'] = distribute_by
            else:
                self.__table__.info['distribute_by_replication'] = True


_MainBase = declarative_base(
    name='MainBase', metaclass=DeclarativeABCMeta
)

_ExperimentBase = declarative_base(
    name='ExperimentBase', metaclass=DeclarativeABCMeta
)


class DateMixIn(object):

    '''Mixin class to automatically add columns with datetime stamps to a
    database table.
    '''

    #: date and time when the row was inserted into the column
    created_at = Column(
        DateTime, default=func.now()
    )

    #: date and time when the row was last updated
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now()
    )


class IdMixIn(object):

    '''Mixin class to automatically add an ID column to a database table
    with primary key constraint.
    '''

    #: int: ID of the object
    id = Column(Integer, primary_key=True)

    @property
    def hash(self):
        '''str: encoded `id`'''
        return utils.encode_pk(self.id)


class MainModel(_MainBase, IdMixIn):

    '''Abstract base class for models of the main database.'''

    __abstract__ = True


class ExperimentModel(_ExperimentBase, IdMixIn):

    '''Abstract base class for models of an experiment-specific database.'''

    __abstract__ = True


class FileSystemModel(ExperimentModel):

    '''Abstract base class for model classes, which refer to data
    stored on disk outside of the database.

    '''

    __abstract__ = True

    _location = Column('location', String(200))

    @abstractproperty
    def location(self):
        '''str: location on disk

        Devired classes must implement `location` as
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
        pass

    @abstractmethod
    def put(self, data):
        pass


registry.register('postgresql.xl', 'tmlib.models.dialect', 'PGXLDialect_psycopg2')


@compiles(DropTable, 'postgresql')
def _compile_drop_table(element, compiler, **kwargs):
    table = element.element
    logger.debug('drop table "%s" with cascade', table.name)
    return compiler.visit_drop_table(element) + ' CASCADE'

