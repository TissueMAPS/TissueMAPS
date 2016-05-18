from flask.ext.uwsgi_websocket import GeventWebSocket
websocket = GeventWebSocket()

from .gc3pie import GC3PieEngine
gc3pie_engine = GC3PieEngine()


from redis import redis_store
from database import db
import auth
