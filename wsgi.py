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
from tmaps.appfactory import create_app


try:
    _execmode = os.environ['TMAPS_EXECMODE']
except KeyError:
    print (
        'No execution mode in the system environment!\n'
        'There has to be a environment variable '
        'TMAPS_EXECMODE that is either '
        ' "DEV", "PROD" or "TEST".'
        ' Using "DEV" as the default.'
    )
    _execmode = 'DEV'
else:
    _execmode = _execmode.upper()  # be case insensitive

cfg = None
if _execmode == 'DEV':
    from tmaps.config import dev
    cfg = dev
elif _execmode == 'TEST':
    from tmaps.config import test
    cfg = test
elif _execmode == 'PROD':
    from tmaps.config import prod
    cfg = prod
else:
    raise (
        'Unknown execution mode %s. '
        'It has to be either "DEV", "TEST" or "PROD". Aborting...' % _execmode
    )


app = create_app(cfg)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='TissueMAPS server')
    parser.add_argument(
        '--port', action='store', type=int, default=5002,
        help='the port on which the server should listen')
    args = parser.parse_args()

    app.run(port=args.port, debug=True)
