from flask import current_app
from passlib.hash import sha256_crypt
import datetime

from flask_jwt import JWT

from tmaps.models import User


jwt = JWT()


@jwt.authentication_handler
def authenticate(username, password):
    """Check if there is a user with this username-pw-combo
    and return the user object if a matching user has been found."""
    user = User.query.filter_by(name=username).first_or_404()
    if user and sha256_crypt.verify(password, user.password):
        return user
    else:
        return None


@jwt.identity_handler
def load_user(payload):
    """Lookup the user for a token payload."""
    user = User.query.get(payload['uid'])
    print payload
    return user


@jwt.jwt_payload_handler
def make_payload(user):
    """Create the token payload for some user"""
    iat = datetime.datetime.utcnow()
    exp = iat + current_app.config.get('JWT_EXPIRATION_DELTA')
    nbf = iat + current_app.config.get('JWT_NOT_BEFORE_DELTA')

    return {
        'uid': user.id,
        'uname': user.name,
        'iat': iat,
        'nbf': nbf,
        'exp': exp
    }


@jwt.jwt_error_handler
def error_handler(e):
    """This function is called whenever flask-jwt encounters an error."""
    print e
    return 'No valid access token in header', 401

