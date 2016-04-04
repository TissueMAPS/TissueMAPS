import os
import logging

import tmlib.models
from tmlib.workflow import Workflow
from tmlib.workflow.api import BasicClusterRoutines

logger = logging.getLogger(__name__)


class WorkflowManager(BasicClusterRoutines):

    '''The *workflow manager* creates workflows (a nested pipeline of
    computational tasks - stages and steps) and submits them to the cluster
    for processing.
    '''

    def __init__(self, experiment_id, verbosity):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of the processed experiment
        verbosity: int
            logging verbosity level
        '''
        super(WorkflowManager, self).__init__()
        self.experiment_id = experiment_id
        self.verbosity = verbosity
        with tmlib.models.utils.Session() as session:
            experiment = session.query(tmlib.models.Experiment).\
                get(self.experiment_id)
            self.workflow_location = experiment.workflow_location

    @property
    def session_location(self):
        '''str: location for the
        `GC3Pie Session <http://gc3pie.readthedocs.org/en/latest/programmers/api/gc3libs/session.html>`_
        '''
        return os.path.join(self.workflow_location, 'session')

    def create_workflow(self, workflow_description=None, waiting_time=0):
        '''Creates a `TissueMAPS` workflow.

        Parameters
        ----------
        workflow_description: tmlib.cfg.WorkflowDescription, optional
            description of a `TissueMAPS` workflow (default: ``None``)
        waiting_time: int, optional
            time in seconds that should be waited upon transition from one
            stage to the other; might be necessary depending on network file
            systems settings (default: ``0``)

        Returns
        -------
        tmlib.workflow.Workflow
        '''
        logger.info('creating workflow')
        with tmlib.models.utils.Session() as session:
            experiment = session.query(tmlib.models.Experiment).\
                get(self.experiment_id)
            submission = tmlib.models.Submission(
                experiment_id=experiment.id
            )
            session.add(submission)
            session.flush()
            submission_id = submission.id

        return Workflow(
            experiment_id=self.experiment_id,
            verbosity=self.verbosity,
            description=workflow_description,
            waiting_time=waiting_time,
            submission_id=submission_id
        )
