import datetime

# Override this key with a secret one
SECRET_KEY = 'secret_key'
HASHIDS_SALT = 'secret_salt'
# This should be set to true in the production config when using NGINX
USE_X_SENDFILE = False
DEBUG = True

# TODO: Set this to an appropriate time
JWT_EXPIRATION_DELTA = datetime.timedelta(minutes=30)
JWT_NOT_BEFORE_DELTA = datetime.timedelta(seconds=0)

POSTGRES_DB_USER = None
POSTGRES_DB_PASSWORD = None
POSTGRES_DB_NAME = None
POSTGRES_DB_HOST = None
POSTGRES_DB_PORT = None

