from flask_sqlalchemy_session import flask_scoped_session
# from flask.ext.sqlalchemy import SQLAlchemy
# db = SQLAlchemy()

from auth import jwt

from spark import Spark
spark = Spark()

from gc3pie import GC3Pie
gc3pie = GC3Pie()

from flask.ext.uwsgi_websocket import GeventWebSocket
websocket = GeventWebSocket()

from flask.ext.redis import FlaskRedis
redis_store = FlaskRedis()


