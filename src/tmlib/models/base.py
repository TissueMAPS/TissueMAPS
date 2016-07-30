'''Abstract base and mixin classes for database models.'''
import os
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta
from sqlalchemy import Column, DateTime, Integer
from sqlalchemy import func
from abc import ABCMeta
from abc import abstractmethod
from abc import abstractproperty

from tmlib import utils


class _DeclarativeABCMeta(DeclarativeMeta, ABCMeta):

    '''Metaclass for abstract declarative base classes.'''


_MainBase = declarative_base(
    name='MainBase', metaclass=_DeclarativeABCMeta
)
_ExperimentBase = declarative_base(
    name='ExperimentBase', metaclass=_DeclarativeABCMeta
)


class DateMixIn(object):

    '''Mixin class to automatically add columns with datetime stamps to a
    database table.

    Attributes
    ----------
    created_at: datetime.datetime
        date and time when the row was inserted into the column
    updated_at: datetime.datetime
        date and time when the row was last updated
    '''

    created_at = Column(
        DateTime, default=func.now()
    )
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now()
    )


class IdMixIn(object):

    '''Mixin class to automatically add an ID column to a database table
    with primary key constraint.

    Attributes
    ----------
    id: int
        unique identifier number
    '''

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


class File(ExperimentModel):

    '''Abstract base class for *files*, which have data attached that are
    stored outside of the database, for example on a file system or an
    object store.
    '''

    __abstract__ = True

    @property
    def format(self):
        '''str: file extension, e.g. ".tif" or ".jpg"'''
        return os.path.splitext(self.name)[1]

    @abstractproperty
    def location(self):
        pass

    @abstractmethod
    def get(self):
        pass

    @abstractmethod
    def put(self, data):
        pass
