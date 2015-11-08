#! /usr/bin/env python
#
"""
Demo the "GC3Pie Engine Status" blueprint for Flask.
"""
# Copyright (C) 2015 S3IT, University of Zurich.
#
# Authors:
#   Riccardo Murri <riccardo.murri@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
from __future__ import absolute_import

__docformat__ = 'reStructuredText'
__version__ = '$Revision$'


# stdlib imports
import logging
import os
import sys

# 3rd party imports
from flask import Flask


# local imports
import gc3libs
import gc3libs.core
import gc3libs.session

from flask_gc3pie import EngineApp


if __name__ == '__main__':
    session = gc3libs.session.Session('TEST')

    f = 1
    if len(session) == 0:
        for n in range(1,6):
            f *= n
            task = gc3libs.Application(
                ['/bin/sleep', f],
                inputs=[],
                outputs=[],
                output_dir=os.path.join(os.getcwd(), "demo_output"),
                stdout=("sleep_{n}.log".format(n=n)),
                join=True,
                jobname=("sleep_{n}".format(n=n)))
            session.add(task)

    demo = EngineApp(session, None, 5, 'demo')

    # set up the Flask web application
    app = Flask(__name__)
    app.debug= True
    app.register_blueprint(demo)

    # tell GC3Pie to use the Flask app logger
    gc3libs.log = app.logger

    # run it
    app.run(host='localhost')
