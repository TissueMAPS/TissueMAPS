import logging
import datetime

DEBUG = True

# Override this key with a secret one
SECRET_KEY = 'default_secret_key'
HASHIDS_SALT = 'default_secret_salt'

## Authentication
JWT_EXPIRATION_DELTA = datetime.timedelta(days=2)
JWT_NOT_BEFORE_DELTA = datetime.timedelta(seconds=0)

## Database
SQLALCHEMY_DATABASE_URI = None
SQLALCHEMY_TRACK_MODIFICATIONS = True

## Logging
LOG_FILE = 'tissuemaps.log'
LOG_LEVEL = logging.INFO
LOG_MAX_BYTES = 2048000  # 2048KB
LOG_N_BACKUPS = 10

## Other
# This should be set to true in the production config when using NGINX
USE_X_SENDFILE = False
REDIS_URL = 'redis://localhost:6379'

## Spark
USE_SPARK = False
SPARK_APP_NAME = 'tmaps'
SPARK_MASTER_URL = 'local'
SPARK_DB_URL = 'postgresql://localhost:5432/tissuemaps'
