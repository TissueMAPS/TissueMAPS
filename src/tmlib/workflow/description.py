import re
import json
from collections import defaultdict
from abc import ABCMeta
from abc import abstractmethod

import tmlib.workflow
from tmlib.workflow.args import VariableArgs
from tmlib.errors import WorkflowDescriptionError


class WorkflowDescription(object):

    '''
    Abstract base class for the description of a `TissueMAPS` workflow.

    A workflow consists of a sequence of *stages*, which are themselves
    composed of *steps*. Each *step* represents a collection of computational
    jobs, which can be submitted for parallel processing on a cluster.

    See also
    --------
    :py:class:`tmlib.tmaps.description.WorkflowStageDescription`
    :py:class:`tmlib.tmaps.description.WorkflowStepDescription`
    '''

    __metaclass__ = ABCMeta

    _PERSISTENT_ATTRS = {'stages', 'type'}

    def __init__(self, stages=None, type=None):
        '''
        Initialize an instance of class WorkflowDescription.

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
        '''
        Returns
        -------
        List[tmlib.tmaps.description.WorkflowStageDescription]
            description of each stage of the workflow
        '''
        return self._stages

    @stages.setter
    def stages(self, value):
        if not isinstance(value, list):
            raise TypeError('Attribute "stages" must have type list')
        if not all([isinstance(v, WorkflowStageDescription) for v in value]):
            raise TypeError(
                'Elements of "steps" must have type WorkflowStageDescription')
        self._stages = value

    @abstractmethod
    def add_stage(self, stage_description):
        '''
        Add an additional stage to the workflow.

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
        '''
        Returns
        -------
        str
            workflow type

        Note
        ----
        There must be a corresponding module in :py:mod:`tmlib.tmaps`
        with the same name.

        Raises
        ------
        AttributeError
            when attribute cannot be determined from class name
        '''
        if self._type is None:
            match = re.match('(\w+)WorkflowDescription',
                             self.__class__.__name__)
            if not match:
                raise AttributeError(
                        'Attribute "type" could not be determined '
                        'from class name')
            self._type = match.group(1).lower()
        return self._type

    @type.setter
    def type(self, value):
        if not isinstance(value, basestring):
            raise TypeError('Attribute "type" must have type basestring.')
        self._type = str(value)

    def __iter__(self):
        for attr in vars(self):
            if attr.startswith('_'):
                attr = re.search(r'^_(.*)', attr).group(1)
            if attr in self._PERSISTENT_ATTRS:
                if attr == 'stages':
                    yield (attr, [dict(s) for s in getattr(self, attr)])
                else:
                    yield (attr, getattr(self, attr))

    def jsonify(self):
        '''
        Returns
        -------
        str
            JSON string encoding the description of the workflow as a
            mapping of key-value pairs
        '''
        d = dict()
        d['type'] = getattr(self, 'type')
        d['stages'] = [json.loads(s.jsonify()) for s in getattr(self, 'stages')]
        return json.dumps(d)


class WorkflowStageDescription(object):

    '''
    Description of a TissueMAPS workflow stage.
    '''

    __metaclass__ = ABCMeta

    _PERSISTENT_ATTRS = {'mode'}

    def __init__(self, name, mode, steps=None):
        '''
        Initialize an instance of class WorkflowStageDescription.

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
        '''
        Returns
        -------
        str
            mode of workflow stage submission
            (options: ``{"sequential", "parallel"}``)
        '''
        return self._mode

    @mode.setter
    def mode(self, value):
        if not isinstance(value, basestring):
            raise TypeError('Attribute "mode" must have type basestring.')
        if value not in {'parallel', 'sequential'}:
            raise ValueError('Attribute "mode" must be either '
                             '"parallel" or "sequential"')
        self._mode = str(value)

    @property
    def steps(self):
        '''
        Returns
        -------
        List[tmlib.tmaps.description.WorkflowStepDescription]
            description of each step that is part of the workflow stage
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
        '''
        Add an additional step to the stage.

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

    def __iter__(self):
        yield ('name', getattr(self, 'name'))
        yield ('mode', getattr(self, 'mode'))
        yield ('steps', [dict(s) for s in getattr(self, 'steps')])

    def jsonify(self):
        '''
        Returns
        -------
        str
            JSON string encoding the description of the stage as a
            mapping of key-value pairs
        '''
        d = defaultdict()
        d['name'] = getattr(self, 'name')
        d['mode'] = getattr(self, 'mode')
        d['steps'] = [json.loads(s.jsonify()) for s in getattr(self, 'steps')]
        return json.dumps(d)


class WorkflowStepDescription(object):

    '''
    Description of a step as part of a TissueMAPS workflow stage.
    '''

    def __init__(self, name, args=None, **kwargs):
        '''
        Initialize an instance of class WorkflowStep.
        Parameters
        ----------
        name: str
            name of the step
        args: dict, optional
            arguments of the step as key-value pairs
        **kwargs: dict, optional
            additional arguments for the description of the step as
            key-value pairs
        Raises
        ------
        TypeError
            when `name` or `args` have the wrong type
        WorkflowDescriptionError
            when a provided argument is not a valid argument for the given step
        '''
        if not isinstance(name, basestring):
            raise TypeError('Argument "name" must have type basestring.')
        self.name = str(name)
        if not(isinstance(args, dict) or args is None):
            raise TypeError('Argument "args" must have type dict.')
        try:
            variable_args_handler = tmlib.workflow.load_var_method_args(self.name, 'init')
        except ImportError:
            raise WorkflowDescriptionError(
                    '"%s" is not a valid step name.' % self.name)
        init_args_handler = tmlib.workflow.load_method_args('init')
        self._args = init_args_handler()
        if args:
            self.args = variable_args_handler(**args)
            for a in args:
                if a not in self.args.variable_args._persistent_attrs:
                    raise WorkflowDescriptionError(
                            'Unknown argument "%s" for step "%s".'
                            % (a, self.name))
        else:
            self.args = variable_args_handler()
        submit_args_handler = tmlib.workflow.load_method_args('submit')
        submit_args = submit_args_handler(**kwargs)
        self.duration = submit_args.duration
        self.memory = submit_args.memory
        self.cores = submit_args.cores

    @property
    def args(self):
        '''
        Returns
        -------
        tmlib.args.GeneralArgs
            all arguments required by the step (i.e. the arguments that can be
            parsed to the `init` method of the step-specific implementation
            of the :py:class:`tmlib.cli.CommandLineInterface` base class)
        Note
        ----
        Default values defined by the step-specific implementation of the
        `Args` class will be used in case an optional argument is not
        provided.
        '''
        return self._args

    @args.setter
    def args(self, value):
        if not isinstance(value, VariableArgs):
            raise TypeError(
                    'Attribute "args" must have type tmlib.args.VariableArgs')
        self._args.variable_args = value

    @property
    def duration(self):
        '''
        Returns
        -------
        str
            time that should be allocated to individual jobs of the step
            in the format "HH:MM:SS"
        '''
        return self._duration

    @duration.setter
    def duration(self, value):
        if not isinstance(value, basestring):
            raise TypeError('Attribute "duration" must have type basestring.')
        match = re.search(r'(?P<h>\d{2}):(?P<m>\d{2}):(?P<s>\d{2})', value)
        results = match.groupdict()
        if any([r is None for r in results.values()]):
            raise ValueError(
                    'Attribute "duration" must have the format "HH:MM:SS"')
        self._duration = str(value)

    @property
    def memory(self):
        '''
        Returns
        -------
        int
            amount of memory that should be allocated to individual jobs of
            the step in gigabytes (GB)
        '''
        return self._memory

    @memory.setter
    def memory(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "memory" must have type int.')
        self._memory = value

    @property
    def cores(self):
        '''
        Returns
        -------
        int
            number of cores that should be allocated to individual jobs of
            the step
        '''
        return self._cores

    @cores.setter
    def cores(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "cores" must have type int.')
        self._cores = value

    def __iter__(self):
        yield ('name', getattr(self, 'name'))
        # Only return the "variable_args" attribute, because these are the
        # arguments that are relevant for the workflow description
        if hasattr(self.args, 'variable_args'):
            yield ('args', dict(getattr(self.args, 'variable_args')))
        else:
            yield ('args', dict())
        if hasattr(self, 'duration'):
            yield ('duration', getattr(self, 'duration'))
        if hasattr(self, 'memory'):
            yield ('memory', getattr(self, 'memory'))
        if hasattr(self, 'cores'):
            yield ('cores', getattr(self, 'cores'))

    def jsonify(self):
        '''
        Returns
        -------
        str
            JSON string encoding the description of the step as a
            mapping of key-value pairs
        '''
        d = defaultdict()
        d['name'] = getattr(self, 'name')
        d['memory'] = getattr(self, 'memory')
        d['duration'] = getattr(self, 'duration')
        d['cores'] = getattr(self, 'cores')
        args = getattr(self.args, 'variable_args')
        d['args'] = json.loads(args.jsonify())
        return json.dumps(d)
