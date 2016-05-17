from flask.ext.uwsgi_websocket import GeventWebSocket
websocket = GeventWebSocket()

from redis import redis_store
from database import db
import auth
