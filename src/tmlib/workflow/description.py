import re
import json
from abc import ABCMeta
from abc import abstractmethod

import tmlib.workflow
from tmlib.errors import WorkflowDescriptionError
from tmlib.workflow.registry import get_step_args
from tmlib.workflow.registry import get_step_api
from tmlib.workflow.args import BatchArguments
from tmlib.workflow.args import SubmissionArguments
from tmlib.workflow.args import ExtraArguments
from tmlib.workflow.args import ArgumentMeta


class WorkflowDescription(object):

    '''Abstract base class for the description of a `TissueMAPS` workflow.

    A workflow consists of a sequence of *stages*, which are themselves
    composed of *steps*. Each *step* represents a collection of computational
    jobs, which can be submitted for parallel processing on a cluster.

    See also
    --------
    :py:class:`tmlib.tmaps.description.WorkflowStageDescription`
    :py:class:`tmlib.tmaps.description.WorkflowStepDescription`
    '''

    __metaclass__ = ABCMeta

    def __init__(self, stages=None, type=None):
        '''
        Parameters
        ----------
        stages: List[tmlib.tmaps.description.WorkflowStageDescription]
            description of each stage of the workflow
        type: str
            workflow type

        Raises
        ------
        tmlib.errors.WorkflowDescriptionError
            when an unknown workflow descriptor is provided
        '''
        self._type = None
        self.stages = list()

    @property
    def stages(self):
        '''List[tmlib.tmaps.description.WorkflowStageDescription]: description
        of each stage of the workflow
        '''
        return self._stages

    @stages.setter
    def stages(self, value):
        if not isinstance(value, list):
            raise TypeError('Attribute "stages" must have type list.')
        if not all([isinstance(v, WorkflowStageDescription) for v in value]):
            raise TypeError(
                'Elements of "steps" must have type WorkflowStageDescription.'
            )
        self._stages = value

    @abstractmethod
    def add_stage(self, stage_description):
        '''Adds an additional stage to the workflow.

        Parameters
        ----------
        stage_description: tmlib.tmaps.description.WorkflowStageDescription
            description of the stage that should be added

        Raises
        ------
        TypeError
            when `stage_description` doesn't have type
            :py:class:`tmlib.tmaps.description.WorkflowStageDescription`
        '''

    @property
    def type(self):
        '''str: workflow type

        Note
        ----
        There must be a corresponding module in :py:mod:`tmlib.workflow`.

        Raises
        ------
        AttributeError
            when attribute cannot be determined from class name
        '''
        # TODO: redo this logic; register workflows
        if self._type is None:
            match = re.match(
                '(\w+)WorkflowDescription', self.__class__.__name__
            )
            if not match:
                raise AttributeError(
                    'Attribute "type" could not be determined from class name'
                )
            self._type = match.group(1).lower()
        return self._type

    @type.setter
    def type(self, value):
        if not isinstance(value, basestring):
            raise TypeError('Attribute "type" must have type basestring.')
        self._type = str(value)

    def as_dict(self):
        '''Returns attributes as key-value pairs.

        Returns
        -------
        dict
        '''
        description = dict()
        description['type'] = self.type
        description['stages'] = [s.as_dict() for s in self.stages]

    def jsonify(self):
        '''Returns attributes as key-value pairs endcoded as JSON.

        Returns
        -------
        str
            JSON string encoding the description of the workflow as a
            mapping of key-value pairs
        '''
        return json.dumps(self.as_dict())


class WorkflowStageDescription(object):

    '''Description of a TissueMAPS workflow stage.'''

    __metaclass__ = ABCMeta

    def __init__(self, name, mode, steps=None):
        '''
        Parameters
        ----------
        name: str
            name of the stage
        mode: str
            mode of workflow stage submission, i.e. whether steps are submitted
            simultaneously or one after another
            (options: ``{"sequential", "parallel"}``) 
        steps: list, optional
            description of individual steps as a mappings of key-value pairs

        Raises
        ------
        TypeError
            when `name` or `steps` have the wrong type
        '''
        if not isinstance(name, basestring):
            raise TypeError('Argument "name" must have type basestring')
        self.name = str(name)
        if steps is not None:
            if not isinstance(steps, list):
                raise TypeError('Argument "steps" must have type list.')
            if not steps:
                raise ValueError('Argument "steps" cannot be empty.')
        self.steps = list()
        self.mode = mode

    @property
    def mode(self):
        '''str: mode of workflow stage submission
        '''
        return self._mode

    @mode.setter
    def mode(self, value):
        if not isinstance(value, basestring):
            raise TypeError('Attribute "mode" must have type basestring.')
        if value not in {'parallel', 'sequential'}:
            raise ValueError(
                'Attribute "mode" must be either "parallel" or "sequential"'
            )
        self._mode = str(value)

    @property
    def steps(self):
        '''List[tmlib.tmaps.description.WorkflowStepDescription]: description
        of each step that is part of the workflow stage
        '''
        return self._steps

    @steps.setter
    def steps(self, value):
        if not isinstance(value, list):
            raise TypeError('Attribute "steps" must have type list')
        if not all([isinstance(v, WorkflowStepDescription) for v in value]):
            raise TypeError(
                'Elements of "steps" must have type WorkflowStepDescription')
        self._steps = value

    @abstractmethod
    def add_step(self, step_description):
        '''Adds an additional step to the stage.

        Parameters
        ----------
        step_description: tmlib.tmaps.description.WorkflowStepDescription
            description of the step that should be added

        Raises
        ------
        TypeError
            when `step_description` doesn't have type
            :py:class:`tmlib.tmaps.description.WorkflowStepDescription`
        '''

    def as_dict(self):
        '''Returns the attributes as key-value pairs.

        Parameters
        ----------
        dict
        '''
        description = dict()
        description['name'] = self.name
        description['mode'] = self.mode
        description['steps'] = [s.as_dict() for s in self.steps]

    def jsonify(self):
        '''Returns the attributes as key-value pairs encoded as JSON.

        Returns
        -------
        str
            JSON string encoding the description of the stage as a
            mapping of key-value pairs
        '''
        return json.dumps(self.as_dict())


class WorkflowStepDescription(object):

    '''Description of a workflow step.'''

    def __init__(self, name, batch_args=dict(), submission_args=dict(),
            extra_args=dict()):
        '''
        Parameters
        ----------
        name: str
            name of the step
        batch_args: dict, optional
            names and values of batch arguments
        submission_args: dict, optional
            names and values of submission arguments 
        extra_args: dict, optional
            names and values of additional arguments

        Raises
        ------
        WorkflowDescriptionError
            when a provided argument is not a valid argument for the given step
        '''
        self.name = str(name)
        batch_args_cls, submission_args_cls, extra_args_cls = get_step_args(name)
        self.batch_args = batch_args_cls(**batch_args)
        self.submission_args = submission_args_cls(**submission_args)
        self._extra_args = None
        if extra_args_cls is not None:
            self.extra_args = extra_args_cls(**extra_args)

    @property
    def extra_args(self):
        '''tmlib.workflow.args.ExtraArguments: extra arguments instance'''
        return self._extra_args

    @extra_args.setter
    def extra_args(self, value):
        if not isinstance(value, ExtraArguments):
            raise TypeError(
                'Attribute "extra_args" must have type '
                'tmlib.workflow.args.ExtraArguments'
            )
        self._extra_args = value

    @property
    def batch_args(self):
        '''tmlib.workflow.args.BatchArguments: batch arguments instance'''
        return self._batch_args

    @batch_args.setter
    def batch_args(self, value):
        if not isinstance(value, BatchArguments):
            raise TypeError(
                'Attribute "batch_args" must have type '
                'tmlib.workflow.args.BatchArguments'
            )
        self._batch_args = value

    @property
    def submission_args(self):
        '''tmlib.workflow.args.BatchArguments: batch arguments instance'''
        return self._submission_args

    @submission_args.setter
    def submission_args(self, value):
        if not isinstance(value, SubmissionArguments):
            raise TypeError(
                'Attribute "submission_args" must have type '
                'tmlib.workflow.args.SubmissionArguments'
            )
        self._submission_args = value

    def as_dict(self):
        '''Returns attributes as key-value pairs.

        Returns
        -------
        dict
        '''
        description = dict()
        description['name'] = self.name
        # TODO: serialize argument collection (only key-value pairs):w

    def jsonify(self):
        '''Returns attributes as key-value pairs encoded as JSON.

        Returns
        -------
        str
            JSON string encoding the description of the step as a
            mapping of key-value pairs
        '''
        return json.dumps(self.as_dict())
