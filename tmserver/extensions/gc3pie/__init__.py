# TmServer - TissueMAPS server application.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
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
from sqlalchemy import func
from flask import current_app

import tmlib.models as tm
from tmlib.workflow.utils import create_gc3pie_sql_store
from tmlib.workflow.utils import create_gc3pie_session
from tmlib.workflow.utils import create_gc3pie_engine
from tmlib.workflow.utils import get_task_status_recursively
from tmlib.workflow.workflow import WorkflowStep, ParallelWorkflowStage

from tmserver.model import encode_pk
from tmserver.extensions.gc3pie.engine import BgEngine

logger = logging.getLogger(__name__)


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

    def init_app(self, app):
        """Initializes the extension for a flask application. This will create
        a *GC3Pie* engine and start it in the background using the "gevent"
        scheduler.

        Parameters
        ----------
        app: flask.Flask
            flask application

        See also
        --------
        :class:`tmserver.extensions.gc3pie.engine.BGEngine`
        """
        logger.info('initialize GC3Pie extension')
        logger.debug('create GC3Pie engine')
        store = create_gc3pie_sql_store()
        engine = create_gc3pie_engine(store)
        bgengine = BgEngine('gevent', engine)
        logger.debug('start GC3Pie engine in the background')
        bgengine.start(10)
        app.extensions['gc3pie'] = {
            'engine': bgengine,
            'store': store,
        }

    @property
    def _engine(self):
        """tmserver.extensions.gc3pie.engine.BgEngine: engine running in the
        background
        """
        return current_app.extensions.get('gc3pie', {}).get('engine')

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
        logger.debug('insert task into tasks table')
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

    def find_task_by_id(self, task_id):
        """Return loaded task with given persistent ID.
        If the task has not been loaded yet, raise `LookupError`.

        Parameters
        ----------
        task_id: int
            persistent task ID

        Returns
        -------
        gc3libs.Task
            computational task
        """
        return self._engine.find_task_by_id(task_id)

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
        self._engine.add(self.retrieve_task(task_id))

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
        logger.info('submit task "%s"', task.jobname)
        logger.debug('add task %d to engine', task.persistent_id)
        self._engine.add(task)

    def kill_task(self, task):
        """Kills submitted task.

        Parameters
        ----------
        task: gc3libs.Task
            computational task
        """
        logger.info('kill task "%s"', task.jobname)
        logger.debug('kill task %d', task.persistent_id)
        # NOTE: The engine requires the exact same task (same Python ID)!
        try:
            task = self._engine.find_task_by_id(task.persistent_id)
        except KeyError:
            logger.error(
                'task "%s" cannot be killed because it is not '
                'actively being processed', task.jobname
            )
            return
        self._engine.kill(task)

    def continue_task(self, task):
        """Continues interrupted task.

        Parameters
        ----------
        task: gc3libs.Task
            computational task
        """
        logger.info('continue task "%s"', task.jobname)
        logger.debug('add task %d to engine', task.persistent_id)
        self._engine.add(task)

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
        # We need to remove the task first, simple addition doesn't update them!
        try:
            self._engine.remove(task)
        except:
            pass
        self._engine.add(task)
        logger.info('resubmit task "%s" at %d', task.jobname, index)
        self._engine.redo(task, index)

    # def set_jobs_to_stopped(self, jobs):
    #     '''Sets the state of jobs to ``STOPPED`` in a recursive manner.

    #     Parameters
    #     ----------
    #     jobs: gc3libs.Task
    #         computational task
    #     '''
    #     def stop_recursively(task_):
    #         task_.execution.state = 'STOPPED'
    #         if hasattr(task_, 'tasks'):
    #             for t in task_.tasks:
    #                 if t.execution.state != gc3libs.Run.State.TERMINATED:
    #                     stop_recursively(t)

    #     stop_recursively(jobs)

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
