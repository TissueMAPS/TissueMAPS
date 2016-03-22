import os
import logging

from .workflow import Workflow
from .api import BasicClusterRoutines
from .. import utils

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

    @utils.auto_create_directory_property
    def project_location(self):
        '''
        Returns
        -------
        str
            location where files required for the step (such as job descriptor
            and log files) will be stored
        '''
        return os.path.join(self.experiment.dir, self.prog_name)

    def create_jobs(self, job_descriptions=None, start_stage=None,
                    start_step=None, waiting_time=120):
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
        waiting_time: int, optional
            time in seconds that should be waited upon transition from one
            stage to the other to avoid issues related to network file systems
            (default: ``120``)

        Returns
        -------
        tmlib.tmaps.workflow.Workflow
        '''
        logger.info('create jobs')
        jobs = Workflow(
                    experiment=self.experiment,
                    verbosity=self.verbosity,
                    description=job_descriptions,
                    start_stage=start_stage,
                    start_step=start_step,
                    waiting_time=waiting_time)
        return jobs
