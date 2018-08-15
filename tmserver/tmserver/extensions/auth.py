# TmServer - TissueMAPS server application.
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
"""JWT-based authentication mechanism for TissueMAPS."""
import datetime

from flask import current_app, request
from flask_sqlalchemy_session import current_session
from passlib.hash import sha256_crypt
from flask_jwt import JWT

import tmlib.models as tm

from tmserver.error import ResourceNotFoundError


jwt = JWT()


# TODO: Use HTTPS for connections to /auth
@jwt.authentication_handler
def authenticate(username, password):
    """Check if there is a user with this username-pw-combo
    and return the user object if a matching user has been found."""
    user = current_session.query(tm.User).filter_by(name=username).one_or_none()
    if not(user and sha256_crypt.verify(password, user.password)):
        raise ResourceNotFoundError(tm.User)
    return user


@jwt.identity_handler
def load_user(payload):
    """Lookup the user for a token payload."""
    # if the scope creates a problem consider using
    # http://flask-sqlalchemy-session.readthedocs.io/en/v1.1/
    user = current_session.query(tm.User).get(payload['uid'])
    return user


@jwt.jwt_payload_handler
def make_payload(user):
    """Create the token payload for some user"""
    iat = datetime.datetime.utcnow()
    exp = iat + current_app.config.get('JWT_EXPIRATION_DELTA')
    nbf = iat + datetime.timedelta(seconds=0)
    return {
        'uid': user.id,
        'uname': user.name,
        'iat': iat,
        'nbf': nbf,
        'exp': exp
    }

# @jwt.jwt_error_handler
# def error_handler(e):
#     """This function is called whenever flask-jwt encounters an error."""
#     return 'No valid access token in header', 401
