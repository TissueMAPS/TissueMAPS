import os
from os.path import join, dirname, abspath
import logging

from flask import Flask

from extensions.database import db
from extensions.auth import jwt
from config import default as default_config


MAIN_DIR_LOCATION = abspath(join(dirname(__file__), os.pardir, os.pardir))
_CLIENT_DIR_LOCATION = join(MAIN_DIR_LOCATION, 'client')
EXPDATA_DIR_LOCATION = join(MAIN_DIR_LOCATION, 'expdata')



def create_app(config):
    """Create a Flask application object that registers all the blueprints on
    which the actual routes are defined.

    The default settings for this app are contained in 'config/default.py'.
    Additional can be supplied to this method as a dict-like config argument.

    """

    # NOTE: The static folder shouldn't for production and is for debug
    # purposes only. The static files will be served by NGINX or similar.
    app = Flask('wsgi',
                static_folder=join(_CLIENT_DIR_LOCATION, 'app'),
                static_url_path='')

    # Load the default settings
    app.config.from_object(default_config)
    app.config.update(config)

    # Add log handlers
    # TODO: Consider adding mail and file handlers if being in a production
    # environment (i.e. app.config.DEBUG == False).
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    stream_handler.setFormatter(formatter)
    app.logger.addHandler(stream_handler)

    if not app.config.get('SQLALCHEMY_DATABASE_URI'):
        raise ValueError('No database URI specified!')

    secret_key = app.config.get('SECRET_KEY')
    if not secret_key:
        raise ValueError('Specify a secret key for this application!')
    if secret_key == 'default_secret_key':
        app.logger.warn('The application will run with the default secret key!')

    salt_string = app.config.get('HASHIDS_SALT')
    if not salt_string:
        raise ValueError(
            'Specify a secret salt string for this application!')
    if salt_string == 'default_salt_string':
        app.logger.warn('The application will run with the default salt string!')

    if app.config['DEBUG']:
        app.logger.info("Starting in __DEBUG__ mode")
    elif app.config['TESTING']:
        app.logger.info("Starting in __TESTING__ mode")
    else:
        app.logger.info("Starting in __PRODUCTION__ mode")

    # Initialize Plugins
    jwt.init_app(app)
    db.init_app(app)

    from api import api
    from res import res

    app.register_blueprint(api, url_prefix='/api')
    app.register_blueprint(res)

    return app
