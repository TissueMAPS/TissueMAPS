import sys
import os
from os.path import join, dirname, abspath
import logging
from flask import Flask
from flask_sqlalchemy_session import flask_scoped_session
import gc3libs

from tmlib.models.utils import (
    create_db_engine, create_db_session_factory, set_db_uri
)

from tmserver import defaultconfig
from tmserver.extensions import jwt
from tmserver.extensions import redis_store
from tmserver.serialize import TmJSONEncoder


logger = logging.getLogger(__name__)


def create_app(config_overrides={}, config_file_location=None, log_level=None):
    """Create a Flask application object that registers all the blueprints on
    which the actual routes are defined.

    The default settings for this app are contained in 'config/default.py'.
    Additional can be supplied to this method as a dict-like config argument.

    """
    app = Flask('wsgi')

    # Load the default settings
    app.config.from_object(defaultconfig)

    if config_file_location is None:
        try:
            config_file_location = os.environ['TMAPS_SETTINGS']
            app.config.from_envvar('TMAPS_SETTINGS')
        except KeyError:
            raise OSError(
                'You need to supply the location of a config file via the '
                'environment variable `TMAPS_SETTINGS`!'
            )

    app.config.update(config_overrides)

    ## Configure logging
    if log_level is None:
        log_level = app.config.get('LOG_LEVEL', logging.INFO)
    app.logger.setLevel(log_level)

    # Remove standard handlers
    app.logger.handlers = []

    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)-40s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # If production mode is activated, set a file logger
    file_handler = logging.handlers.RotatingFileHandler(
        app.config['LOG_FILE'],
        maxBytes=app.config['LOG_MAX_BYTES'],
        backupCount=app.config['LOG_N_BACKUPS'])
    file_handler.setFormatter(formatter)
    stdout_handler = logging.StreamHandler(stream=sys.stdout)
    stdout_handler.setFormatter(formatter)
    app.logger.addHandler(file_handler)
    app.logger.addHandler(stdout_handler)
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.setLevel(log_level)
    werkzeug_logger.addHandler(file_handler)
    werkzeug_logger.addHandler(stdout_handler)
    flask_jwt_logger = logging.getLogger('flask_jwt')
    flask_jwt_logger.setLevel(log_level)
    flask_jwt_logger.addHandler(file_handler)
    flask_jwt_logger.addHandler(stdout_handler)
    tmserver_logger = logging.getLogger('tmserver')
    tmserver_logger.setLevel(log_level)
    tmserver_logger.addHandler(file_handler)
    tmserver_logger.addHandler(stdout_handler)
    wsgi_logger = logging.getLogger('wsgi')
    wsgi_logger.setLevel(log_level)
    wsgi_logger.addHandler(file_handler)
    wsgi_logger.addHandler(stdout_handler)
    tmlib_logger = logging.getLogger('tmlib')
    tmlib_logger.setLevel(log_level)
    tmlib_logger.addHandler(file_handler)
    tmlib_logger.addHandler(stdout_handler)
    gc3pie_logger = logging.getLogger('gc3.gc3libs')
    gc3pie_logger.setLevel(logging.WARN)
    gc3pie_logger.addHandler(file_handler)
    gc3pie_logger.addHandler(stdout_handler)
    apscheduler_logger = logging.getLogger('apscheduler')
    apscheduler_logger.setLevel(logging.CRITICAL)
    apscheduler_logger.addHandler(file_handler)
    apscheduler_logger.addHandler(stdout_handler)

    app.logger.info('Loaded config: "%s"' % config_file_location)

    ## Set the JSON encoder
    app.json_encoder = TmJSONEncoder

    if not app.config.get('SQLALCHEMY_DATABASE_URI'):
        app.logger.critical(
            'No database URI specified! The application config needs to have '
            'the entry SQLALCHEMY_DATABASE_URI = '
            'postgresql://USER:PASS@HOST:PORT/DBNAME')
        sys.exit(1)

    secret_key = app.config.get('SECRET_KEY')
    if not secret_key:
        app.logger.critical('Specify a secret key for this application!')
        sys.exit(1)
    if secret_key == 'default_secret_key':
        app.logger.warn('The application will run with the default secret key!')

    app.logger.info(
        'Starting mode: %s' % (
        'DEBUG' if app.config['DEBUG'] else (
            'TESTING' if app.config['TESTING'] else 'PRODUCTION'
        )))

    if 'TMAPS_STORAGE_HOME' in app.config:
        os.environ['TMAPS_STORAGE_HOME'] = app.config['TMAPS_STORAGE_HOME']
        app.logger.info(
            'Setting TMAPS_STORAGE_HOME to: %s' % app.config['TMAPS_STORAGE_HOME']
        )

    ## Initialize Plugins
    jwt.init_app(app)
    redis_store.init_app(app)

    # Create a session scope for interacting with the main database
    db_uri = set_db_uri(app.config['SQLALCHEMY_DATABASE_URI'])
    engine = create_db_engine(db_uri)
    session_factory = create_db_session_factory(engine)
    session = flask_scoped_session(session_factory, app)

    if app.config.get('USE_SPARK', False):
        from tmserver.extensions import spark
        spark.init_app(app)

    from tmserver.extensions import gc3pie
    gc3pie.init_app(app)

    ## Import and register blueprints
    from api import api
    app.register_blueprint(api, url_prefix='/api')

    from jtui.api import jtui
    # from tmserver.extensions import websocket
    # websocket.init_app(app)
    app.register_blueprint(jtui, url_prefix='/jtui')

    # @app.after_request
    # def after_request(response):
    #   response.headers.add('Access-Control-Allow-Origin', '*')
    #   response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    #   response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    #   return response

    return app
