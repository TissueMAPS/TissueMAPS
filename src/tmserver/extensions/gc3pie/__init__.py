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

logger = logging.getLogger(__name__)


class GC3Pie(object):

    def __init__(self, app=None):
        """An extension that creates a `GC3Pie` engine to submit computational
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
        self.interval = 1
        gc3libs_logger = logging.getLogger('gc3.gc3libs')
        gc3libs_logger.setLevel(logging.CRITICAL)
        apscheduler_logger = logging.getLogger('apscheduler')
        apscheduler_logger.setLevel(logging.CRITICAL)
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

        Returns
        -------
        gc3libs.session.Session
            session

        See also
        --------
        :py:class:`tmlib.models.Submission`
        :py:class:`tmlib.models.Task`
        """
        logger.debug('insert jobs into tasks table')
        persistent_id = self._store.save(jobs)
        logger.debug('update submissions table')
        with tm.utils.MainSession() as session:
            submission = session.query(tm.Submission).get(jobs.submission_id)
            submission.top_task_id = persistent_id

    def retrieve_jobs(self, experiment_id, program):
        """Retrieves the top level job for the given `experiment`
        from the store that were most recently submitted by `program`.

        Parameters
        ----------
        experiment_id: int
            ID of the processed experiment
        program: str
            name of the program that submitted the jobs, e.g. ``"jtui"``

        Returns
        -------
        gc3libs.Task or gc3libs.workflow.TaskCollection
            jobs

        See also
        --------
        :py:class:`tmlib.models.Submission`
        :py:class:`tmlib.models.Task`
        """
        # submission_manager = SubmissionManager(experiment.id, 'workflow')
        # task_id = submission_manager.get_task_id_for_last_submission()
        with tm.utils.MainSession() as session:
            last_submission_id = session.query(func.max(tm.Submission.id)).\
                filter(
                    tm.Submission.experiment_id == experiment_id,
                    tm.Submission.program == program
                ).\
                group_by(tm.Submission.experiment_id).\
                one_or_none()
            if last_submission_id is not None:
                last_submission_id = last_submission_id[0]
                last_submission = session.query(tm.Submission).\
                    get(last_submission_id)
                job_id = last_submission.top_task_id
                if job_id is None:
                    return None
                return self._store.load(job_id)
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
        self._engine.kill(jobs)
        self._engine.progress()

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
        self._engine.remove(jobs)
        # self._engine.add(jobs)
        logger.info('redo jobs')
        self._engine.redo(jobs, index)

    def get_status_of_submitted_jobs(self, jobs):
        '''Gets the status of submitted jobs.

        Parameters
        ----------
        jobs: gc3libs.Task or gc3libs.workflow.TaskCollection
            individual computational task or collection of tasks

        Returns
        -------
        dict
            status of jobs

        See also
        --------
        :py:function:`tmlib.workflow.utils.get_task_data_from_sql_store`
        '''
        return get_task_data_from_sql_store(jobs)
