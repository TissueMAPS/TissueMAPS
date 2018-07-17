#! /usr/bin/env python
#
"""
Job daemon: manage and progress tasks in an existing DB session.

This code basically only instanciates the stock ``SessionBasedDaemon``
class: no new tasks are ever created (as the ``new_tasks`` hook, and the
``created``/``modified``/``deleted`` handlers are not overridden), but one
must connect to the XML-RPC interface to manage existing tasks.
"""
# Copyright (C) 2018, University of Zurich. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import (absolute_import, division, print_function)

from fnmatch import fnmatch
import os
from os.path import basename
import sys

import gc3libs
from gc3libs.cmdline import SessionBasedDaemon
from gc3libs.session import Session

from tmlib.globals import idfactory
from tmlib.workflow.utils import get_gc3pie_store_extra_fields


class DbProcessingDaemon(SessionBasedDaemon):
    """
    Run a given command on all files created within the given inbox
    directories.  Each command runs as a separate GC3Pie task.
    Task and session management is possible using the usual server
    XML-RPC interface.
    """

    # setting `version` is required to instanciate the
    # `SessionBasedDaemon` class
    version = '1.3'

    # set up processing of positional arguments on the command line
    def setup_args(self):
        # no command-line arguments are accepted or needed here; still
        # we need to ensure that `self.params.inbox` is set to a valid
        # empty sequence, otherwise `self.parse_args()` will error out
        self.params.inbox = []

    def _make_session(self, session_uri, store_url):
        # We rule out "simulated" sessions (the `TemporarySession`
        # class from `gc3libs.session`) because in that case there's
        # no index so *all* jobs will be loaded, which in even
        # moderate TM usage leads to out-of-memory errors soon.
        assert session_uri.scheme == 'file', (
            "tm_jobdaemon can only manage directory-based sessions!"
        )
        self.log.info(
            "Creating session at %s, storing tasks at %s ...",
            session_uri, store_url)
        return Session(
            session_uri.path,
            create=True,
            store_or_url=store_url,
            extra_fields=get_gc3pie_store_extra_fields(),
            idfactory=idfactory,
        )

    def make_task_controller(self):
        """
        Create GC3Pie `Engine`:class: the same way TM server does.

        In contrast to `tmlib.workflow.utils.create_gc3pie_engine`,
        no limit to the number of "in flight" tasks is set here;
        if you want to cap it, use the ``-J`` command-line option.
        """
        engine = super(DbProcessingDaemon, self).make_task_controller()
        # additional settings
        engine.forget_terminated = True
        engine.retrieve_overwrites = True
        return engine

## main: run server

if "__main__" == __name__:
    from tm_jobdaemon import DbProcessingDaemon
    DbProcessingDaemon().run()
