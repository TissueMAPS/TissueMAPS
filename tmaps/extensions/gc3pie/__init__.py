import os
import logging
import gc3libs
import collections
from sqlalchemy import func
from flask import current_app

from tmaps.extensions import db

import tmlib.models as tm
from tmlib.workflow import BgEngine
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
        gc3libs_logger.setLevel(logging.DEBUG)
        apscheduler_logger = logging.getLogger('apscheduler')
        apscheduler_logger.setLevel(logging.DEBUG)
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
        engine = create_gc3pie_engine(store)
        bgengine = BgEngine('threading', engine)
        logger.info('start GC3Pie engine in the background')
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

    def _get_session(self, experiment):
        return create_gc3pie_session(experiment.session_location, self._store)

    def store_jobs(self, experiment, jobs):
        """Stores jobs to in `GC3Pie` session to make them persistent.

        Parameters
        ----------
        experiment: tmlib.models.Experiment
            experiment object
        jobs: gc3libs.Task or gc3libs.workflow.TaskCollection
            individual computational task or collection of tasks

        Returns
        -------
        gc3libs.session.Session
            session

        Note
        ----
        When the session already exists it is simply returned, otherwise
        a new session is created.
        """
        logger.debug('insert jobs into tasks table')
        self._store.save(jobs)
        logger.debug('update submissions table')
        submission = db.session.query(tm.Submission).\
            get(jobs.submission_id)
        submission.top_task_id = jobs.persistent_id
        db.session.add(submission)
        db.session.commit()

    def retrieve_jobs(self, experiment, submitting_program):
        """Retrieves jobs of the most recent submission for the given
        `experiment` from the store.

        Parameters
        ----------
        experiment: tmlib.models.Experiment
            processed experiment
        submitting_program: str
            program that submitted the jobs, e.g. ``"jtui"``

        Returns
        -------
        gc3libs.Task or gc3libs.workflow.TaskCollection
            jobs
        """
        last_submission_id = db.session.query(func.max(tm.Submission.id)).\
            filter(
                tm.Submission.experiment_id == experiment.id,
                tm.Submission.program == submitting_program
            ).\
            group_by(tm.Submission.experiment_id).\
            one_or_none()
        if last_submission_id is not None:
            last_submission_id = last_submission_id[0]
            last_submission = db.session.query(tm.Submission).\
                get(last_submission_id)
            job_id = last_submission.top_task_id
            return self._store.load(job_id)
        else:
            return None

    def submit_jobs(self, jobs):
        """Submits jobs to the cluster.

        Parameters
        ----------
        jobs: gc3libs.Task or gc3libs.workflow.TaskCollection
            individual computational task or collection of tasks

        Returns
        -------
        int
            submission ID
        """
        logger.info('add jobs to engine')
        self._engine.add(jobs)

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
