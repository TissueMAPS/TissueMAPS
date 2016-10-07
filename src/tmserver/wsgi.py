# -*- coding: utf-8 -*-
"""
This module holds an application instance that is passed to a server such as
gunicorn or uWSGI.

Depending on the environment variable ``TMAPS_SETTINGS``,
different configurations will be loaded.

"""
from tmserver.appfactory import create_app

app = create_app()

