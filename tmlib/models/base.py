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
'''Abstract base and mixin classes for database models.

Mixin classes must implement additional table columns using the
`declared_attr <http://docs.sqlalchemy.org/en/latest/orm/extensions/declarative/api.html#sqlalchemy.ext.declarative.declared_attr>`_
decorator.

'''
import os
import logging
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
        distribution_column = (
            d.pop('__distribute_by_hash__', None) or
            getattr(self, '__bind_key__', None)
        )
        distribute_by_replication = (
            d.pop('__distribute_by_replication__', False)
        )
        colocated_table = (
            d.pop('__colocate_with__', None)
        )
        DeclarativeMeta.__init__(self, name, bases, d)
        if hasattr(self, '__table__'):
            if distribution_column is not None:
                columns = self.__table__.c
                if distribution_column not in columns:
                    raise ValueError(
                        'Specified distribution column "%s" '
                        'is not a column of table "%s".'
                        % (distribution_column, self.__table__.name)
                    )
                self.__table__.info['distribute_by_hash'] = distribution_column
                self.__table__.info['colocated_table'] = colocated_table
                self.is_distributed = True
            elif distribute_by_replication:
                self.__table__.info['distribute_by_replication'] = True
                self.is_distributed = True
            else:
                self.is_distributed = False


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
        return Column(DateTime, default=func.now())

    @declared_attr
    def updated_at(cls):
        '''datetime: date and time when the row was last updated'''
        # TODO: CREATE TRIGGER to update independent of ORM
        return Column(DateTime, default=func.now(), onupdate=func.now())


class IdMixIn(object):

    '''Mixin class to automatically add an ID column to a database table
    with primary key constraint.
    '''

    #: int: ID assigned to the object by the database
    id = Column(BigInteger, primary_key=True, autoincrement=True)

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

