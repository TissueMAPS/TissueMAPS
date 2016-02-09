import os
import logging
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
