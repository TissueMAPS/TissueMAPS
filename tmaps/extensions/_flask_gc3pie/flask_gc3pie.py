#! /usr/bin/env python
#
"""
A minimal web application for checking the status of a GC3Pie session.

Provides a REST API to perform the basic GC3Pie operations on jobs,
plus a status page reporting some basic metrics.

It is implemented as a `Flask <http://flask.pocoo.org/>` "blueprint"
for easier embedding into larger web applications.

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


# 3rd party imports
from flask import current_app
from flask import _app_ctx_stack as stack

import gc3libs
from tmlib import engine as tmlib_engine


class GC3PieEngine(object):
    """
    A flask extension to perform the core GC3Pie operations on tasks
    in the given `session`.

    """

    def __init__(self, *args, **kwargs):
        if len(args) > 0 or len(kwargs) > 0:
            self.init_app(*args, **kwargs)

    def init_app(self, app, session, poll_interval, engine=None):
        """
        Construct an `GC3PieEngine` Flask extension object.

        First argument `session` is a `gc3libs.session.Session`
        instance. Tasks belonging to the session can then be operated
        on through the methods exposed by this class.

        Argument `engine` must be a valid GC3Pie `Engine`:class:
        instance.  All tasks in the session will be attached to this
        engine.  If argument `engine` has the special value ``None``,
        then a new `Engine`:class: instance is created using
        `self._create_engine()`.

        Method `Engine.progress`:meth: is called every `poll_interval`
        seconds in a separate thread in order to update task status.
        This thread can be controlled using the `start`:meth: and
        `stop`:meth: methods.

        """
        self._app = app
        self._session = session
        self.delay = poll_interval
        self._bg = tmlib_engine.BgEngine(
            'threading',
            engine if engine is not None else self._create_engine())
        for task in self._session:
            self._bg.add(task)

    def _create_engine(self):
        """
        Create and return a `gc3libs.core.Engine`:class: instance.

        The default implementation just calls the
        `gc3libs.create_engine` factory method. Override in order to
        specialize creation.

        """
        return gc3libs.create_engine()

    def get_status_data(self):
        return {
            'stats': self._bg.get_stats_data(),
            'tasks': self._bg.all_tasks_data()
        }

    def get_task_info(self, task):
        return self._bg.get_task_data(task)

    def kill(self, task_id):
        if task_id not in self._session.tasks:
            raise ValueError('No task with id %s within this session.' % task_id)
        else:
            self._bg.kill(self._session.tasks[task_id])
            return True

    # def ready(self):
    #     # try to extract nodename from HTTP request
    #     addr = request.remote_addr
    #     hostname = request.environ['HTTP_REMOTE_HOST'] if ('HTTP_REMOTE_HOST' in request.environ) else None
    #     # look for POST/GET parameters
    #     auth = request.values['auth']
    #     nodename = request.values['hostname']
    #     # perform registration
    #     nodename = nodename.split('.')[0]
    #     log.info("Host '%s' (%s) registering as node '%s'",
    #              (hostname if hostname is not None else "<UNKNOWN>"),
    #              (addr if addr is not None else "unknown address"),
    #              nodename)
    #     self.vm_is_ready(auth, nodename)
    #     return 'OK'
