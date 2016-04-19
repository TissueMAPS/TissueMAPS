import os


TESTING = False
DEBUG = True

SQLALCHEMY_DATABASE_URI = os.environ['TMAPS_DB_URI']

REDIS_URL = 'redis://localhost:6379'

