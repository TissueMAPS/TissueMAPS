from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, DateTime, Integer
from sqlalchemy import func

from . import utils

_Base = declarative_base()


class Model(_Base):

    '''
    Abstract base class for a `TissueMAPS` model,
    which maps Python classes to relational database tables.
    '''

    __abstract__ = True

    #: Table columns
    id = Column(Integer, primary_key=True)
    created_on = Column(
        DateTime, default=func.now()
    )
    updated_on = Column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    @property
    def hash(self):
        '''
        Returns
        -------
        str
            encoded ID
        '''
        return utils.encode_pk(self.id)
