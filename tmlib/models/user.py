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
from passlib.hash import sha256_crypt
from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from tmlib.models.base import MainModel, DateMixIn


class User(MainModel, DateMixIn):

    '''A `TissueMAPS` *user*.

    Attributes
    ----------
    name: str
        user name
    email: str
        email address
    password: str
        password
    '''

    __tablename__ = 'users'

    #: str: username
    name = Column(String, index=True, unique=True, nullable=False)

    #: str: email
    email = Column(String, unique=True, nullable=False)

    #: str: encoded password
    password = Column(String, nullable=False)

    #: List[tmlib.models.experiment.ExperimentReferences]: references to
    #: owned experiments
    experiments = relationship('ExperimentReference', back_populates='user')

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
        return '<User(id=%r, name=%r)>' % (self.id, self.name)
