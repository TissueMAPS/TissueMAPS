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

import os
import os.path as p
from werkzeug.contrib.profiler import ProfilerMiddleware
import flask
from tmaps.appfactory import create_app
from tmaps import log

logo = """
  _____ _                    __  __    _    ____  ____
 |_   _(_)___ ___ _   _  ___|  \/  |  / \  |  _ \/ ___|
   | | | / __/ __| | | |/ _ \ |\/| | / _ \ | |_) \___ \\
   | | | \__ \__ \ |_| |  __/ |  | |/ ___ \|  __/ ___) |
   |_| |_|___/___/\__,_|\___|_|  |_/_/   \_\_|   |____/

"""

print logo

app = create_app()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='TissueMAPS server')
    parser.add_argument(
        '--port', action='store', type=int, default=5002,
        help='the port on which the server should listen')
    parser.add_argument(
        '--threaded', action='store_true', default=False,
        help='if the dev server should run in multi-threaded mode')
    parser.add_argument(
        '--profile', action='store_true', default=False,
        help='if application should be profiled')
    args = parser.parse_args()

    if args.profile:
        app.config['PROFILE'] = True
        app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[30])

    use_jtui = app.config.get('USE_JTUI', False)
    if use_jtui:
        if args.threaded:
            app.run(port=args.port, debug=True, gevent=100, threaded=True)
        else:
            app.run(port=args.port, debug=True, gevent=100)
    else:
        app.run(port=args.port, debug=True, threaded=args.threaded)
