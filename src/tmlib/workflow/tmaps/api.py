import os
import logging

import tmlib.models as tm
from tmlib.readers import YamlReader
from tmlib.workflow.workflow import Workflow
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
        with tm.utils.Session() as session:
            experiment = session.query(tm.Experiment).\
                get(self.experiment_id)
            self.workflow_description = experiment.workflow_description

    def create_workflow(self, submission_id, user_name,
            workflow_description=None, waiting_time=0):
        '''Creates a `TissueMAPS` workflow.

        Parameters
        ----------
        submission_id: int
            ID of the corresponding submission
        user_name: str
            name of the submitting user
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

        if workflow_description is None:
            workflow_description = self.workflow_description

        return Workflow(
            experiment_id=self.experiment_id,
            verbosity=self.verbosity,
            submission_id=submission_id,
            user_name=user_name,
            description=workflow_description,
            waiting_time=waiting_time,
        )



