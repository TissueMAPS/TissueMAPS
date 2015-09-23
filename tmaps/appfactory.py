import os
from os.path import join, dirname, abspath

from flask import Flask

from extensions.database import db
from extensions.auth import jwt
from extensions.websocket import ws
from config import dev


MAIN_DIR_LOCATION = abspath(join(dirname(__file__), os.pardir, os.pardir))
CLIENT_DIR_LOCATION = join(MAIN_DIR_LOCATION, 'client')
EXPDATA_DIR_LOCATION = join(MAIN_DIR_LOCATION, 'expdata')


# Execute the modules auth and models after having defined
# the plugin instances.
import models


def create_app(config_object=dev):
    """Create a Flask application object that registers all the blueprints on
    which the actual routes are defined. Creating the application in a function
    that is then to be called by run.py allows for easier testing.

    The default settings for this app are contained in 'config/default.py'.
    For the execution modes 'test', 'dev', and 'production', the respective file
    (e.g. 'config/dev.py') must exist in the config directory.

    """

    # TODO: The static folder shouldn't for production and is for debug
    # purposes only. The static files will be served by NGINX or similar.
    app = Flask('wsgi',
                static_folder=join(CLIENT_DIR_LOCATION, 'app'),
                static_url_path='')

    app.config.from_object(config_object)

    db_access_keys = [
        'POSTGRES_DB_USER',
        'POSTGRES_DB_PASSWORD',
        'POSTGRES_DB_HOST',
        'POSTGRES_DB_PORT',
        'POSTGRES_DB_NAME'
    ]

    db_access_vals = [app.config.get(k) for k in db_access_keys]
    for k, v in zip(db_access_keys, db_access_keys):
        if not v:
            raise Exception('Key %s has to be specified in config!' % k)

    dbuser, dbpassword, dbhost, dbport, dbname = db_access_vals

    SQLALCHEMY_DATABASE_URI = 'postgresql://{user}:{password}@{host}:{port}/{dbname}'.format(
        user=dbuser,
        password=dbpassword,
        host=dbhost,
        port=str(dbport),
        dbname=dbname
    )
    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI

    secret_key = app.config.get('SECRET_KEY')
    if not secret_key or secret_key == 'secret_key':
        print '[warning] specify a __secret__ key for this application!'
    salt_string = app.config.get('HASHIDS_SALT')
    if not salt_string or secret_key == 'salt_string':
        print '[warning] specify a __secret__ salt string for this application!'

    # TODO: Include better logging support
    if app.config['DEBUG']:
        print "[info] Starting in __DEBUG__ mode"
    else:
        print "[info] Starting in __PRODUCTION__ mode"

    # Initialize Plugins
    jwt.init_app(app)
    db.init_app(app)
    # ws.init_app(app)

    from api import api
    from res import res

    app.register_blueprint(api, url_prefix='/api')
    app.register_blueprint(res)

    return app
