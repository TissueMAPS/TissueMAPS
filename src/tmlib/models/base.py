'''Abstract base and mixin classes for database models.
'''
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, DateTime, Integer
from sqlalchemy_imageattach.entity import Image
from sqlalchemy import func

from tmlib import utils

_Base = declarative_base()


class DateMixIn(object):

    '''Mixin class to add datetime stamps.

    Attributes
    ----------
    created_on: datetime.datetime
        date and time when the row was inserted into the column
    updated_on: datetime.datetime
        date and time when the row was last updated
    '''

    created_on = Column(
        DateTime, default=func.now()
    )
    updated_on = Column(
        DateTime, default=func.now(), onupdate=func.now()
    )


class Pixels(_Base, Image):

    '''Abstract base class for *pixels*, which represent the actual binary data
    in an image file.
    '''

    __abstract__ = True


class Model(_Base):

    '''Abstract base class for a `TissueMAPS` database model.
    
    It maps Python classes to relational tables.

    Attributes
    ----------
    id: int
        unique identifier number
    '''

    __abstract__ = True

    # Table columns
    id = Column(Integer, primary_key=True)
