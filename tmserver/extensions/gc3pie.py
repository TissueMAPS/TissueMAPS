# TmServer - TissueMAPS server application.
# Copyright (C) 2016-2018  University of Zurich
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
import os
import logging
import gc3libs
import collections
from random import random
from sqlalchemy import func
from time import sleep
import xmlrpclib

from flask import current_app

import tmlib.models as tm
from tmlib.workflow.utils import (
    create_gc3pie_sql_store,
    create_gc3pie_session,
    create_gc3pie_engine,
    get_task_status_recursively,
)
from tmlib.workflow.workflow import WorkflowStep, ParallelWorkflowStage

from tmserver import cfg
from tmserver.model import encode_pk

logger = logging.getLogger(__name__)


def start_job_daemon(max_delay=0, jobdaemon_program=None,
                     jobdaemon_host=None, jobdaemon_port=None,
                     store_url=None, session_dir=None):
    """
    Start the GC3Pie "job daemon".

    Actual startup of the child process is delayed by a random amount
    up to *max_delay* seconds.  By default *max_delay* is 0 (i.e. the
    job daemon process is started immediately) but this can be used to
    avoid multiple concurrent starts from separate threads.
    """
    # we cannot simply use `cfg.*` as default values, since Python
    # evaluates default values when reading the function definition
    jobdaemon = jobdaemon_program or cfg.jobdaemon
    if jobdaemon_host is None:
        jobdaemon_host = cfg.jobdaemon_host
    if jobdaemon_port is None:
        jobdaemon_port = cfg.jobdaemon_port
    if store_url is None:
        store_url = cfg.db_master_uri + '#table=tasks'
    if session_dir is None:
        session_dir = cfg.jobdaemon_session
    sleep(max_delay * random())
    logger.info("Trying to start GC3Pie job daemon.")
    os.spawnlp(os.P_NOWAIT, jobdaemon,
               jobdaemon,
               '--session', session_dir,
               '--store-url', store_url,
               '--listen', (jobdaemon_host + ':' + jobdaemon_port))


class GC3Pie(object):

    """
    A Flask extension that exposes a *GC3Pie* engine to manage computational tasks.
    """

    def __init__(self, app=None):
        """
        Parameters
        ----------
        app: flask.Flask, optional
            flask application (default: ``None``)

        Note
        ----
        The preferred way of initializing the extension is via the
        `init_app()` method.

        Examples
        --------
        gc3pie = GC3Pie()
        gc3pie.init_app(app)
        """
        if app is not None:
            self.init_app(app)


    def init_app(self, app, jobdaemon_url=None):
        """
        Start the GC3Pie job daemon process and connect to the DB.

        Parameters
        ----------
        app: flask.Flask
            flask application
        """
        logger.info('initializing GC3Pie extension ...')
        if jobdaemon_url:
            if jobdaemon_url.startswith('http'):
                self._jobdaemon_url = jobdaemon_url
            else:
                self._jobdaemon_url = 'http://' + jobdaemon_url
        else:
            # build it from host and port
            self._jobdaemon_url = cfg.jobdaemon_url
        app.extensions['gc3pie'] = {
            'store': create_gc3pie_sql_store(),
            'client': self._connect_to_job_daemon(),
        }


    def _connect_to_job_daemon(self, timeout=60, delay=0, max_pause=5):
        sleep(delay * random())
        waited = 0
        while True:
            try:
                client = xmlrpclib.ServerProxy(self._jobdaemon_url)
                logger.debug(
                    "Connected to GC3Pie job daemon at %s",
                    self._jobdaemon_url)
                return client
            except Exception as err:
                logger.info(
                    "Cannot connect to GC3Pie job daemon `%s`: %s",
                    self._jobdaemon_url, err)
                if waited > timeout:
                    logger.debug(
                        "Could not connect within %ds, giving up ...",
                        timeout)
                    break
                start_job_daemon()
                wait = max_pause * random()
                logger.debug("Trying to connect again in %ds ...", wait)
                sleep(wait)
                waited += wait
        return None


    def _job_daemon_do(self, cmd, *args):
        try:
            func = getattr(self._client, cmd, *args)
        except AttributeError:
            msg = ("Job daemon exports no command named `{cmd}`."
                   .format(cmd=cmd))
            self.log.error(msg)
            raise AssertionError(msg)
        try:
            result = func(*args)
        except xmlrpclib.Fault as err:
            logger.error(
                "Error running job daemon command `%s`: %s",
                cmd, err.faultString)
            raise
        if result.startswith('ERROR'):
            msg =("Error running job daemon command `{0}`: {1}"
                  .format(cmd, result[len('ERROR: '):]))
            logger.error(msg)
            raise RuntimeError(msg)
        return result


    @property
    def _client(self):
        """
        Return XML-RPC client for communicating with the job daemon.
        """
        return current_app.extensions.get('gc3pie', {}).get('client')

    @property
    def _store(self):
        """gc3libs.persistence.sql.SqlStore: SQL store for job persistence
        """
        return current_app.extensions.get('gc3pie', {}).get('store')

    def store_task(self, task):
        """Stores task in the database.

        Parameters
        ----------
        task: gc3libs.Task
            computational task or collection of computational tasks
        """
        logger.debug('insert task `%s` into tasks table', task)
        persistent_id = self._store.save(task)
        logger.debug('update submissions table')
        with tm.utils.MainSession() as session:
            submission = session.query(tm.Submission).get(task.submission_id)
            submission.top_task_id = persistent_id

    def get_id_of_most_recent_submission(self, experiment_id, program):
        """Gets the ID of the most recent
        :class:`Submission <tmlib.models.submission.Submission>`.

        Parameters
        ----------
        experiment_id: int
            ID of the processed experiment
        program: str
            name of the program that submitted the task

        Returns
        -------
        int
        """
        with tm.utils.MainSession() as session:
            submission_id = session.query(func.max(tm.Submission.id)).\
                filter(
                    tm.Submission.experiment_id == experiment_id,
                    tm.Submission.program == program
                ).\
                group_by(tm.Submission.experiment_id).\
                one_or_none()
            if submission_id is not None:
                return submission_id[0]
            else:
                return None

    def get_id_of_most_recent_task(self, experiment_id, program):
        """Gets the ID of the top level task for the given `experiment`
        that was most recently submitted by `program`.

        Parameters
        ----------
        experiment_id: int
            ID of the processed
            :class:`Experiment <tmlib.models.experiment.Experiment>`
        program: str
            name of the program that submitted the task, e.g. ``"workflow"``

        Returns
        -------
        int
        """
        submission_id = self.get_id_of_most_recent_submission(
            experiment_id, program
        )
        if submission_id is not None:
            with tm.utils.MainSession() as session:
                submission = session.query(tm.Submission).get(submission_id)
                task_id = submission.top_task_id
        else:
            task_id = None
        return task_id

    def retrieve_most_recent_task(self, experiment_id, program):
        """Retrieves the top level task for the given `experiment`
        from the store that was most recently submitted by `program`.

        Parameters
        ----------
        experiment_id: int
            ID of the processed
            :class:`Experiment <tmlib.models.experiment.Experiment>`
        program: str
            name of the program that submitted the task, e.g. ``"workflow"``

        Returns
        -------
        gc3libs.Task
        """
        task_id = self.get_id_of_most_recent_task(experiment_id, program)
        if task_id is not None:
            return self._store.load(task_id)
        else:
            return None

    def manage_task(self, task_id):
        """Add the task with the given ID to the running Engine.

        Parameters
        ----------
        task_id: int
            persistent task ID

        Returns
        -------
        None
        """
        logger.debug(
            'Handing over task ID %s to GC3Pie job daemon ...',
            task_id)
        self._job_daemon_do('manage', task_id)

    def retrieve_task(self, task_id):
        """Retrieves a task from the store.

        Parameters
        ----------
        task_id: int
            persistent task ID

        Returns
        -------
        gc3libs.Task
            computational task
        """
        return self._store.load(task_id)

    def submit_task(self, task):
        """Submits task.

        Parameters
        ----------
        task: gc3libs.Task
            computational task
        """
        logger.info(
            'Submitting task "%s" (ID: %s) ...',
            task.jobname, task.persistent_id)
        self._job_daemon_do('manage', str(task.persistent_id))

    def kill_task(self, task):
        """Kills submitted task.

        Parameters
        ----------
        task: gc3libs.Task
            computational task
        """
        logger.info(
            'Killing task "%s" (ID: %s) ...',
            task.jobname, task.persistent_id)
        self._job_daemon_do('kill', str(task.persistent_id))

    def kill_task_by_id(self, task_id):
        """Kills submitted task.

        Parameters
        ----------
        task: gc3libs.Task
            computational task
        """
        logger.info('Killing task with ID %s ...', task_id)
        self._job_daemon_do('kill', str(task_id))

    def resubmit_task(self, task, index=0):
        """Resubmits a task.

        Parameters
        ----------
        task: gc3libs.Task
            computational task
        index: int, optional
            index of an individual task within a sequential collection of tasks
            from where all subsequent tasks should be resubmitted
        """
        logger.info(
            'Resubmit task "%s" (ID: %s) from sub-task #%d ...',
            task.jobname, task.persistent_id, index)
        self._job_daemon_do('redo', str(task.persistent_id), str(index))

    def get_task_status(self, task_id, recursion_depth=None):
        '''Gets the status of submitted task.

        Parameters
        ----------
        task_id: int
            ID of the :class:`Task <tmlib.models.submission.Task>`
        recursion_depth: int, optional
           recursion depth for querying subtasks

        Returns
        -------
        dict
            status of task

        See also
        --------
        :func:`tmlib.workflow.utils.get_task_status_recursively`
        '''
        return get_task_status_recursively(
            task_id, recursion_depth, encode_pk
        )
