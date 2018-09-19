# TmServer - TissueMAPS server application.
# Copyright (C) 2016-2018 University of Zurich.
# Copyright (C) 2018  University of Zurich
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import sys
import os
from os.path import join, dirname, abspath
import logging
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from flask_sqlalchemy_session import flask_scoped_session
from flask import Flask, jsonify
import gc3libs

import tmlib.models as tm
from tmlib.log import map_logging_verbosity
from tmlib.models.utils import (
    create_db_engine, create_db_tables, create_db_session_factory
)

from tmserver.extensions import jwt
from tmserver.serialize import TmJSONEncoder
from tmserver.error import register_http_error_classes
from tmserver import cfg


logger = logging.getLogger(__name__)



def create_app(verbosity=None):
    """Creates a Flask application object that registers all the blueprints on
    which the actual routes are defined.

    Parameters
    ----------
    verbosity: int, optional
        logging verbosity to override the
        :attr:`logging_verbosity <tmserver.config.ServerConfig.logging_verbosity>`
        setting in the configuration file (default: ``None``)

    Returns
    -------
    flask.Flask
        Flask application

    """
    log_formatter = logging.Formatter(
        fmt='%(process)5d/%(threadName)-12s| %(levelname)-8s| %(message)s [[%(name)s @ %(pathname)s:%(lineno)d]]',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    log_handler = logging.StreamHandler(stream=sys.stdout)
    log_handler.setFormatter(log_formatter)
    if verbosity is None:
        verbosity = cfg.logging_verbosity
    log_level = map_logging_verbosity(verbosity)

    app = Flask('wsgi')
    app.config['PROPAGATE_EXCEPTIONS'] = True

    app.logger.handlers = []  # remove standard handlers
    app.logger.setLevel(log_level)
    app.logger.addHandler(log_handler)

    tmserver_logger = logging.getLogger('tmserver')
    tmserver_logger.setLevel(log_level)
    tmserver_logger.addHandler(log_handler)

    tmlib_logger = logging.getLogger('tmlib')
    tmlib_logger.setLevel(log_level)
    tmlib_logger.addHandler(log_handler)

    flask_jwt_logger = logging.getLogger('flask_jwt')
    flask_jwt_logger.setLevel(log_level)
    flask_jwt_logger.addHandler(log_handler)

    gevent_logger = logging.getLogger('gevent')
    gevent_logger.addHandler(log_handler)
    gc3pie_logger = logging.getLogger('gc3.gc3libs')
    gc3pie_logger.addHandler(log_handler)
    sqlalchemy_logger = logging.getLogger('sqlalchemy.engine')
    sqlalchemy_logger.addHandler(log_handler)
    wsgi_logger = logging.getLogger('wsgi')
    wsgi_logger.addHandler(log_handler)
    if verbosity > 4:
        gevent_logger.setLevel(logging.DEBUG)
        gc3pie_logger.setLevel(logging.DEBUG)
        sqlalchemy_logger.setLevel(logging.DEBUG)
        wsgi_logger.setLevel(logging.DEBUG)
    elif verbosity > 3:
        gevent_logger.setLevel(logging.INFO)
        gc3pie_logger.setLevel(logging.INFO)
        sqlalchemy_logger.setLevel(logging.INFO)
        wsgi_logger.setLevel(logging.INFO)
    else:
        gevent_logger.setLevel(logging.ERROR)
        gc3pie_logger.setLevel(logging.ERROR)
        sqlalchemy_logger.setLevel(logging.ERROR)
        wsgi_logger.setLevel(logging.ERROR)

    app.json_encoder = TmJSONEncoder

    if cfg.secret_key == 'default_secret_key':
        app.logger.warn('The application will run with the default secret key!')
    elif not cfg.secret_key:
        app.logger.critical('Specify a secret key for this application!')
        sys.exit(1)
    app.config['SECRET_KEY'] = cfg.secret_key

    app.config['JWT_EXPIRATION_DELTA'] = cfg.jwt_expiration_delta

    ## Error handling

    # Register custom error classes
    register_http_error_classes(app)

    # Register SQLAlchemy error classes
    @app.errorhandler(NoResultFound)
    def _handle_no_result_found(error):
        response = jsonify(error={
            'message': error.message,
            'status_code': 400,
            'type': error.__class__.__name__
        })
        logger.error('no result found: ' + error.message)
        response.status_code = 400
        return response

    @app.errorhandler(MultipleResultsFound)
    def _multiple_results_found(error):
        response = jsonify(error={
            'message': error.message,
            'status_code': 409,
            'type': error.__class__.__name__
        })
        logger.error('multiple results found: ' + error.message)
        response.status_code = 409
        return response

    @app.errorhandler(IntegrityError)
    def _handle_integrity_error(error):
        response = jsonify(error={
            'error': True,
            'message': error.message,
            'status_code': 500,
            'type': error.__class__.__name__
        })
        logger.error('database integrity error: ' + error.message)
        response.status_code = 500
        return response


    ## Initialize Plugins
    jwt.init_app(app)

    # Create a session scope for interacting with the main database
    engine = create_db_engine(cfg.db_master_uri)
    create_db_tables(engine)
    session_factory = create_db_session_factory()
    session_factory.configure(bind=engine)
    session = flask_scoped_session(session_factory, app)

    from tmserver.extensions import gc3pie
    gc3pie.init_app(app)

    ## Import and register blueprints
    from tmserver.api import api
    app.register_blueprint(api, url_prefix='/api')

    from tmserver.jtui import jtui
    app.register_blueprint(jtui, url_prefix='/jtui')

    # For uWSGI fork()
    engine.dispose()

    return app
