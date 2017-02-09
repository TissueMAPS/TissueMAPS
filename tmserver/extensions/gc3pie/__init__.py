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

from tmserver.extensions.gc3pie.engine import BgEngine

import tmlib.models as tm
from tmlib.workflow.utils import create_gc3pie_sql_store
from tmlib.workflow.utils import create_gc3pie_session
from tmlib.workflow.utils import create_gc3pie_engine
from tmlib.workflow.utils import get_task_data_from_sql_store
from tmlib.workflow.workflow import WorkflowStep, ParallelWorkflowStage

logger = logging.getLogger(__name__)


class GC3Pie(object):

    def __init__(self, app=None):
        """An extension that exposes a `GC3Pie` engine to submit computational
        jobs to a batch cluster.

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
        gc3pie.engine.add(jobs)
        """
        self.interval = 10
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize the extension for some flask application. This will create
        a `GC3Pie` engine and start it in the background using the "gevent"
        scheduler.

        Parameters
        ----------
        app: flask.Flask
            flask application
        """
        logger.info('initialize GC3Pie extension')
        logger.info('create GC3Pie engine')
        store = create_gc3pie_sql_store()
        engine = create_gc3pie_engine(store, forget=True)
        # NOTE: gevent scheduler is not available on localhost when app is
        # started debug mode via run_simple()
        app.config.setdefault('SCHEDULER', 'gevent')
        scheduler = app.config.get('SCHEDULER')
        bgengine = BgEngine(scheduler, engine)
        logger.info(
            'start GC3Pie engine in the background using "%s" scheduler',
            scheduler
        )
        bgengine.start(self.interval)
        app.extensions['gc3pie'] = {
            'engine': bgengine,
            'store': store,
        }

    @property
    def _engine(self):
        """tmlib.workflow.BgEngine: `GC3Pie` engine running in the background
        in a different thread
        """
        return current_app.extensions.get('gc3pie', {}).get('engine')

    @property
    def _store(self):
        """gc3libs.persistence.sql.SqlStore: `GC3Pie` store for job persistence
        """
        return current_app.extensions.get('gc3pie', {}).get('store')

    def store_jobs(self, jobs):
        """Stores jobs in the database.

        Parameters
        ----------
        jobs: gc3libs.Task or gc3libs.workflow.TaskCollection
            individual computational task or collection of tasks

        See also
        --------
        :class:`tmlib.models.Submission`
        :class:`tmlib.models.Task`
        """
        logger.debug('insert jobs into tasks table')
        persistent_id = self._store.save(jobs)
        logger.debug('update submissions table')
        if hasattr(jobs, 'submission_id'):
            with tm.utils.MainSession() as session:
                submission = session.query(tm.Submission).\
                    get(jobs.submission_id)
                submission.top_task_id = persistent_id

    def get_id_of_last_submission(self, experiment_id, program):
        """Gets the ID of the most recent submitted by `program` for
        experiment with id `experiment_id`.

        Parameters
        ----------
        experiment_id: int
            ID of the processed experiment
        program: str
            name of the program that submitted the jobs

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
                return submission_id

    def retrieve_jobs(self, experiment_id, program):
        """Retrieves the top level job for the given `experiment`
        from the store that were most recently submitted by `program`.

        Parameters
        ----------
        experiment_id: int
            ID of the processed experiment
        program: str
            name of the program that submitted the jobs, e.g. ``"workflow"``

        Returns
        -------
        gc3libs.Task or gc3libs.workflow.TaskCollection

        See also
        --------
        :class:`tmlib.models.Submission`
        :class:`tmlib.models.Task`
        """
        # submission_manager = SubmissionManager(experiment.id, 'workflow')
        # task_id = submission_manager.get_task_id_for_last_submission()
        submission_id = self.get_id_of_last_submission(experiment_id, program)
        if submission_id is not None:
            with tm.utils.MainSession() as session:
                submission = session.query(tm.Submission).get(submission_id)
                job_id = submission.top_task_id
            if job_id is not None:
                return self._store.load(job_id)
            else:
                return None
        else:
            return None

    def retrieve_single_job(self, job_id):
        """Retrieves an individual job from the store.

        Parameters
        ----------
        job_id: int
            persistent job Id

        Returns
        -------
        gc3libs.Task or gc3libs.TaskCollection
            job
        """
        return self._store.load(job_id)

    def submit_jobs(self, jobs):
        """Submits jobs to the cluster.

        Parameters
        ----------
        jobs: gc3libs.Task or gc3libs.workflow.TaskCollection
            individual computational task or collection of tasks
        """
        logger.info('add jobs to engine')
        self._engine.add(jobs)

    def kill_jobs(self, jobs):
        """Kills jobs running on the cluster.

        Parameters
        ----------
        jobs: gc3libs.Task or gc3libs.workflow.TaskCollection
            individual computational task or collection of tasks
        """
        logger.info('kill jobs')
        original_task = self._engine.find_task_by_id(jobs.persistent_id)
        logger.debug('kill task %d', original_task.persistent_id)
        self._engine.kill(original_task)
        self._engine.progress()

    def continue_jobs(self, jobs):
        """Continous jobs that have been interrupted.

        Parameters
        ----------
        jobs: gc3libs.Task or gc3libs.workflow.TaskCollection
            individual computational task or collection of tasks
        """
        logger.info('update jobs in engine')
        self._engine.add(jobs)

    def resubmit_jobs(self, jobs, index=0):
        """Resubmits jobs to the cluster.

        Parameters
        ----------
        jobs: gc3libs.Task or gc3libs.workflow.TaskCollection
            individual computational task or collection of tasks
        index: int, optional
            index of an individual task within a sequential collection of tasks
            from where all subsequent tasks should be resubmitted
        """
        logger.info('update jobs in engine')
        # We need to remove the jobs first, simple addition doesn't update them!
        try:
            self._engine.remove(jobs)
        except:
            pass
        self._engine.add(jobs)
        logger.info('redo jobs "%s" at %d', jobs.jobname, index)
        self._engine.redo(jobs, index)

    def set_jobs_to_stopped(self, jobs):
        '''Sets the state of jobs to ``STOPPED`` in a recursive manner.

        Parameters
        ----------
        jobs: gc3libs.Task or gc3libs.workflow.TaskCollection
            individual computational task or collection of tasks
        '''
        def stop_recursively(task_):
            task_.execution.state = 'STOPPED'
            if hasattr(task_, 'tasks'):
                for t in task_.tasks:
                    if t.execution.state != gc3libs.Run.State.TERMINATED:
                        stop_recursively(t)

        stop_recursively(jobs)

    def get_status_of_submitted_jobs(self, jobs, recursion_depth=None):
        '''Gets the status of submitted jobs.

        Parameters
        ----------
        jobs: gc3libs.Task or gc3libs.workflow.TaskCollection
            individual computational task or collection of tasks
        recursion_depth: int, optional
           recursion depth for querying subtasks

        Returns
        -------
        dict
            status of jobs

        See also
        --------
        :func:`tmlib.workflow.utils.get_task_data_from_sql_store`
        '''
        return get_task_data_from_sql_store(jobs, recursion_depth)
