import sys
import os
from os.path import join, dirname, abspath
import logging

from flask import Flask
import gc3libs

from tmaps import defaultconfig
from tmaps.extensions import db
from tmaps.extensions.auth import jwt
from tmaps.extensions.redis import redis_store
# from tmaps.extensions.gc3pie import gc3pie_engine
from tmaps.serialize import TmJSONEncoder

log = logging.getLogger(__name__)


def create_app(config_overrides={}):
    """Create a Flask application object that registers all the blueprints on
    which the actual routes are defined.

    The default settings for this app are contained in 'config/default.py'.
    Additional can be supplied to this method as a dict-like config argument.

    """
    app = Flask('wsgi')

    # Load the default settings
    app.config.from_object(defaultconfig)

    settings_location = os.environ.get('TMAPS_SETTINGS')
    if not settings_location:
        log.error(
            'You need to supply the location of a config file via the '
            'environment variable `TMAPS_SETTINGS`!')
        sys.exit(1)
    else:
        app.config.from_envvar('TMAPS_SETTINGS')
        log.info('Loaded config: "%s"' % settings_location)

    app.config.update(config_overrides)

    # Set the JSON encoder
    app.json_encoder = TmJSONEncoder

    if not app.config.get('SQLALCHEMY_DATABASE_URI'):
        raise ValueError('No database URI specified!')

    secret_key = app.config.get('SECRET_KEY')
    if not secret_key:
        raise ValueError('Specify a secret key for this application!')
    if secret_key == 'default_secret_key':
        log.info('The application will run with the default secret key!')

    log.info(
        'Starting mode: %s' % (
        'DEBUG' if app.config['DEBUG'] else (
            'TESTING' if app.config['TESTING'] else 'PRODUCTION'
        )))

    if 'TMAPS_STORAGE' in app.config:
        os.environ['TMAPS_STORAGE'] = app.config['TMAPS_STORAGE']
        log.info('Setting TMAPS_STORAGE to: %s' % app.config['TMAPS_STORAGE'])

    # Initialize Plugins
    jwt.init_app(app)
    db.init_app(app)
    redis_store.init_app(app)
    # gc3pie_engine.init_app(app)

    # Import and register blueprints
    from api import api

    app.register_blueprint(api, url_prefix='/api')

    # @app.after_request
    # def after_request(response):
    #   response.headers.add('Access-Control-Allow-Origin', '*')
    #   response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    #   response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    #   return response

    return app
