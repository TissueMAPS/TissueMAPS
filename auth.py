from models import User
from passlib.hash import sha256_crypt

from flask_jwt import JWT

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


@jwt.user_handler
def load_user(payload):
    """Lookup the user for a token payload."""
    user = User.query.get(payload['uid'])
    return user


@jwt.payload_handler
def make_payload(user):
    """Create the token payload for some user"""
    return {
        'uid': user.id,
        'uname': user.name
    }


@jwt.error_handler
def error_handler(e):
    """This function is called whenever flask-jwt encounters an error."""
    return 'No valid access token in header', 401
