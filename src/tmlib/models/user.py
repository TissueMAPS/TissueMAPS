from passlib.hash import sha256_crypt
from sqlalchemy import Column, String

from tmlib.models import Model


class User(Model):

    '''A *user*.

    Attributes
    ----------
    name: str
        user name
    email: str
        email address
    password: str
        password
    '''

    #: Name of the corresponding database table
    __tablename__ = 'users'

    #: Table columns
    name = Column(String, index=True, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)

    def __init__(self, name, email, password):
        '''
        Parameters
        ----------
        name: str
            user name
        email: str
            email address
        password: str
            password
        '''
        self.name = name
        self.email = email
        self.password = sha256_crypt.encrypt(password)

    def __repr__(self):
        return '<User(id=%r, name=%r)' % (self.id, self.name)
