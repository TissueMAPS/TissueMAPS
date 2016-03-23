from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, DateTime, Integer
from sqlalchemy import func

from tmlib import utils

_Base = declarative_base()


class DateMixIn(object):

    '''
    Mixin class to add datetime stamps "created_on" and "updated_on" to a
    declarative class.
    '''

    created_on = Column(
        DateTime, default=func.now()
    )
    updated_on = Column(
        DateTime, default=func.now(), onupdate=func.now()
    )


class Model(_Base):

    '''Abstract base class for a `TissueMAPS` model.
    
    It maps Python classes to relational database tables.

    Attributes
    ----------
    id: int
        unique global identifier
    created_on: datetime.datetime
        datetime of creation
    updated_on: datetime.datetime
        datetime of last modification
    '''

    __abstract__ = True

    # Table columns
    id = Column(Integer, primary_key=True)

    @property
    def hash(self):
        '''str: encoded `id`'''
        return utils.encode_pk(self.id)
