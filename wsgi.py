# -*- coding: utf-8 -*-
"""
This module holds an application instance that is passed to a server such as
gunicorn or uWSGI.

Depending on the environment variable ``TMAPS_EXECMODE``,
different configs will be loaded. This variable should be set to ``DEV``,
``TEST``, or ``PROD``. The associated configs are named ``DevConfig``,
``TestConfig``, and ``ProdConfig`` and should be importable from the config
module.

If this module is executed directly, the application is executed by a flask
development server.

"""

import os.path as p
import flask
from tmaps.appfactory import create_app
import logging


cfg = flask.Config(p.realpath(p.dirname(__file__)))

# Will throw a RuntimeError if not provided
cfg.from_envvar('TMAPS_SETTINGS')

app = create_app(cfg)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='TissueMAPS server')
    parser.add_argument(
        '--port', action='store', type=int, default=5002,
        help='the port on which the server should listen')
    parser.add_argument(
        '--threaded', action='store_true', default=False,
        help='if the dev server should run in multi-threaded mode')
    args = parser.parse_args()

    app.run(port=args.port, debug=True, threaded=args.threaded)
