import os
import logging

import tmlib.models
from tmlib.readers import YamlReader
from tmlib.workflow.registry import get_workflow_description
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
        with tmlib.models.utils.Session() as session:
            experiment = session.query(tmlib.models.Experiment).\
                get(self.experiment_id)
            self.workflow_location = experiment.workflow_location

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
            workflow_description = self.description

        return Workflow(
            experiment_id=self.experiment_id,
            verbosity=self.verbosity,
            submission_id=submission_id,
            user_name=user_name,
            description=workflow_description,
            waiting_time=waiting_time,
        )

    @property
    def description(self):
        '''tmlib.workflow.tmaps.description.WorkflowDescription: description
        of the workflow

        Raises
        ------
        TypeError
            when description obtained from file is not a mapping
        KeyError
            when description obtained from file doesn't have key "type"
        '''
        filename = os.path.join(
            self.workflow_location, 'workflow_description.yaml'
        )
        with YamlReader(filename) as f:
            description = f.read()
        if not isinstance(description, dict):
            raise TypeError('Description must be a mapping.')
        if 'type' not in description:
            raise KeyError('Description must have key "type".')
        workflow_description_class = get_workflow_description(
            description['type']
        )
        return workflow_description_class(description['stages'])


