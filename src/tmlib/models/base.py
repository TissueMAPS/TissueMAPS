import base64

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, DateTime, Integer
from sqlalchemy import func

Base = declarative_base()


def decode_pk(pk_str):
    return int(base64.urlsafe_b64decode(str(pk_str))[5:])


def encode_pk(pk):
    return base64.urlsafe_b64encode('tmaps' + str(pk))


class Model(Base):

    id = Column(Integer, primary_key=True)

    created_on = Column(DateTime, default=func.now())
    updated_on = Column(
        DateTime, default=func.now(), onupdate=func.now())

    @property
    def hash(self):
        return encode_pk(self.id)
