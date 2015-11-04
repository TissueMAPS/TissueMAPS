import datetime

# Override this key with a secret one
SECRET_KEY = 'default_secret_key'
HASHIDS_SALT = 'default_secret_salt'

# This should be set to true in the production config when using NGINX
USE_X_SENDFILE = False
DEBUG = True

JWT_EXPIRATION_DELTA = datetime.timedelta(days=2)
JWT_NOT_BEFORE_DELTA = datetime.timedelta(seconds=0)

POSTGRES_DB_USER = None
POSTGRES_DB_PASSWORD = None
POSTGRES_DB_NAME = None
POSTGRES_DB_HOST = None
POSTGRES_DB_PORT = None

REDIS_URL = 'redis://localhost:6379'

SQLALCHEMY_TRACK_MODIFICATIONS = True
