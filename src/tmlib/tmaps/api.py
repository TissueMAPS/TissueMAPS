import os
import logging
import shutil
from gc3libs.session import Session
from .workflow import Workflow
from ..api import BasicClusterRoutines

logger = logging.getLogger(__name__)


class WorkflowClusterRoutines(BasicClusterRoutines):

    def __init__(self, experiment, prog_name, verbosity):
        '''
        Initialize an instance of class WorkflowClusterRoutines.

        Parameters
        ----------
        experiment: tmlib.experiment.Experiment
            configured experiment object
        prog_name: str
            name of the corresponding program (command line interface)
        verbosity: int
            logging verbosity level
        '''
        super(WorkflowClusterRoutines, self).__init__(experiment)
        self.experiment = experiment
        self.prog_name = prog_name
        self.verbosity = verbosity

    @property
    def project_dir(self):
        '''
        Returns
        -------
        str
            directory where *.job* files and log output will be stored
        '''
        self._project_dir = os.path.join(self.experiment.dir, self.prog_name)
        if not os.path.exists(self._project_dir):
            logging.debug('create project directory: %s' % self._project_dir)
            os.mkdir(self._project_dir)
        return self._project_dir

    @property
    def session_dir(self):
        '''
        Returns
        -------
        str
            absolute path the
            `GC3Pie session <http://gc3pie.readthedocs.org/en/latest/programmers/api/gc3libs/session.html>`_
            directory
        '''
        return os.path.join(self.project_dir, 'cli_session')

    def create_jobs(self, job_descriptions=None,
                    start_stage=None, start_step=None):
        '''
        Create a `TissueMAPS` workflow.

        Parameters
        ----------
        job_descriptions: tmlib.cfg.WorkflowDescription, optional
            description of a `TissueMAPS` workflow (default: ``None``)
        start_stage: str, optional
            name of the stage from which the workflow should be started
            (default: ``None``)
        start_step: str, optional
            name of the step in `start_stage` from which the workflow should be
            started (default: ``None``)

        Returns
        -------
        tmlib.tmaps.workflow.Workflow
            custom implementation of a GC3Pie sequential task collection
        '''
        logger.info('create jobs')
        jobs = Workflow(
                    experiment=self.experiment,
                    verbosity=self.verbosity,
                    description=job_descriptions,
                    start_stage=start_stage,
                    start_step=start_step)
        return jobs

    def create_session(self, jobs, overwrite=True, backup=False):
        '''
        Create a `GC3Pie session <http://gc3pie.readthedocs.org/en/latest/programmers/api/gc3libs/session.html>`_for job persistence.

        Parameters
        ----------
        jobs: tmlib.tmaps.workflow.Workflow
            jobs that should be added to the session
        overwrite: bool, optional
            overwrite an existing session (default: ``True``)
        backup: bool, optional
            backup an existing session (default: ``False``)

        Note
        ----
        If `backup` or `overwrite` are set to ``True`` a new session will be
        created, otherwise a session existing from a previous submission
        will be re-used.
        '''
        logger.info('create session')
        if overwrite:
            if os.path.exists(self.session_dir):
                logger.debug('remove session directory: %s', self.session_dir)
                shutil.rmtree(self.session_dir)
        elif backup:
            current_time = self.create_datetimestamp()
            backup_dir = '%s_%s' % (self.session_dir, current_time)
            logger.debug('create backup of session directory: %s', backup_dir)
            shutil.move(self.session_dir, backup_dir)
        session = Session(self.session_dir)
        if overwrite:
            logger.debug('add jobs to session')
            session.add(jobs)
            logger.debug('save session to disk')
            session.save_all()
        return session
