# -*- coding: utf-8 -*-
"""
This module holds an application instance that is passed to a server such as
gunicorn or uWSGI.

"""
from tmserver.appfactory import create_app

app = create_app()

