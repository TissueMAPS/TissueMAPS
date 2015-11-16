import re
import os
import importlib
from abc import ABCMeta
from abc import abstractmethod
from abc import abstractproperty
from ..args import VariableArgs
from ..errors import WorkflowDescriptionError


def load_method_args(method_name):
    '''
    Load general arguments that can be parsed to a method of
    an implemented subclass of a :py:class:`tmlib.cli.CommandLineInterface`
    base class

    Parameters
    ----------
    method_name: str
        name of the method

    Returns
    -------
    tmlib.args.Args
        argument container

    Raises
    ------
    AttrbuteError
        when the "args" module doesn't contain a method-specific
        implementation of the `Args` base class
    '''
    module_name = 'tmlib.args'
    module = importlib.import_module(module_name)
    class_name = '%sArgs' % method_name.capitalize()
    return getattr(module, class_name)


def load_var_method_args(prog_name, method_name):
    '''
    Load variable program-specific arguments that can be parsed to
    a method of an implemented subclass of a
    :py:class:`tmlib.cli.CommandLineInterface` base class.

    Parameters
    ----------
    prog_name: str
        name of the program
    method_name: str
        name of the method

    Returns
    -------
    tmlib.args.Args
        argument container

    Note
    ----
    Returns ``None`` when the "args" module in the subpackage with name
    `prog_name` doesn't contain a program- and method-specific implementation
    of the `Args` base class.

    Raises
    ------
    ImportError
        when subpackage with name `prog_name` doesn't have a module named "args"
    '''
    package_name = 'tmlib.%s' % prog_name
    module_name = 'tmlib.%s.args' % prog_name
    importlib.import_module(package_name)
    module = importlib.import_module(module_name)
    class_name = '%s%sArgs' % (prog_name.capitalize(),
                               method_name.capitalize())
    try:
        return getattr(module, class_name)
    except AttributeError:
        return None


class WorkflowDescription(object):

    '''
    Abstract base class for the description of a TissueMAPS workflow.

    A workflow consists of *stages*, which themselves are made up of *steps*.

    Each *step* represents a collection of individual tasks, which can be
    processed in parallel on a computer cluster.

    The workflow is described by a mapping of key-value pairs::

        mapping = {
            "workflow":
                "type": ""
                "stages": [
                    {
                        "name": "",
                        "steps": [
                            {
                                "name": "",
                                "args": {}
                            },
                            ...
                        ]
                    },
                    ...
                ]
        }

    A WorkflowDescription can be constructed from a mapping and converted
    back to a mapping::

        >>>obj = WorkflowDescription(**mapping)
        >>>dict(obj)

    Warning
    -------
    The input mapping will not be identical to the output mapping, because
    default values will be added for optional arguments that are not provided.

    See also
    --------
    :py:class:`tmlib.tmaps.description.WorkflowStageDescription`
    :py:class:`tmlib.tmaps.description.WorkflowStepDescription`
    '''

    __metaclass__ = ABCMeta

    _PERSISTENT_ATTRS = {
        'stages', 'virtualenv', 'type'
    }

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class WorkflowDescription.

        Parameters
        ----------
        **kwargs: dict, optional
            workflow descriptors as key-value pairs

        Raises
        ------
        tmlib.errors.WorkflowDescriptionError
            when an unknown workflow descriptor is provided
        '''
        # Set defaults
        self._type = None
        self.virtualenv = None
        # Check stage description
        for k in kwargs.keys():
            if k not in self._PERSISTENT_ATTRS:
                raise WorkflowDescriptionError(
                        'Unknown workflow descriptor: "%s"' % k)
        self.stages = list()

    @property
    def stages(self):
        '''
        Returns
        -------
        List[tmlib.tmaps.description.WorkflowStageDescription]
            description of each in the workflow
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

    @property
    def virtualenv(self):
        '''
        Returns
        -------
        str
            name of a Python virtual environment that needs to be activated
            (default: ``None``)

        Note
        ----
        Requires the environment variable "$WORKON_HOME" to point to the
        virtual environment home directory, i.e. the directory where
        `virtualenv` is located.

        See also
        --------
        `virtualenvwrapper <http://virtualenvwrapper.readthedocs.org/en/latest/>`_
        '''
        return self._virtualenv

    @virtualenv.setter
    def virtualenv(self, value):
        if value is not None:
            if 'WORKON_HOME' not in os.environ:
                raise KeyError('No environment variable "WORKON_HOME".')
            virtualenv_dir = os.path.join(os.environ['WORKON_HOME'], value)
            if not os.path.exists(virtualenv_dir):
                raise OSError('Virtual environment does not exist: %s'
                              % virtualenv_dir)
        self._virtualenv = value

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


class WorkflowStageDescription(object):

    '''
    Description of a TissueMAPS workflow stage.
    '''

    __metaclass__ = ABCMeta

    def __init__(self, name, steps=None, **kwargs):
        '''
        Initialize an instance of class WorkflowStageDescription.

        Parameters
        ----------
        name: str
            name of the stage
        steps: list, optional
            description of individual steps as a mapping of key-value pairs
        **kwargs: dict, optional
            description of a workflow stage in form of key-value pairs

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
        yield ('steps', [dict(s) for s in getattr(self, 'steps')])


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
            description of the step as key-value pairs

        Raises
        ------
        TypeError
            when `name` or `args` have the wrong type
        WorkflowDescriptionError
            when a provided argument is not valid for the given step
        '''
        if not isinstance(name, basestring):
            raise TypeError('Argument "name" must have type basestring.')
        self.name = str(name)
        if not(isinstance(args, dict) or args is None):
            raise TypeError('Argument "args" must have type dict.')
        try:
            variable_args_handler = load_var_method_args(self.name, 'init')
        except ImportError:
            raise WorkflowDescriptionError(
                    '"%s" is not a valid step name.' % self.name)
        args_handler = load_method_args('init')
        self._args = args_handler()
        if args:
            self.args = variable_args_handler(**args)
            for a in args:
                if a not in self.args.variable_args._persistent_attrs:
                    raise WorkflowDescriptionError(
                            'Unknown argument "%s" for step "%s".'
                            % (a, self.name))
        else:
            self.args = variable_args_handler()

    @property
    def args(self):
        '''
        Returns
        -------
        tmlib.args.GeneralArgs
            all arguments required by the step (i.e. the arguments that can be
            parsed to the `init` method of the program-specific implementation
            of the :py:class:`tmlib.cli.CommandLineInterface` base class)

        Note
        ----
        Default values defined by the program-specific implementation of the
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
            memory that should be allocated to individual jobs of the step
            in gigabytes (GB)
        '''
        return self._memory

    @memory.setter
    def memory(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "memory" must have type int.')
        self._memory = value

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
