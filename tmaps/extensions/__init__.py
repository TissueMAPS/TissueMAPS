from flask.ext.redis import FlaskRedis
redis_store = FlaskRedis()

from flask.ext.sqlalchemy import SQLAlchemy
db = SQLAlchemy()

from auth import jwt

from spark import Spark
spark = Spark()
