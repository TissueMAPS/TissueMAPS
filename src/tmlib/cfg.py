import os
import logging
from . import utils
from . import logging_utils
from .tmaps import workflow
from .tmaps import canonical
from .plate import Plate
from .args import GeneralArgs
from .writers import YamlWriter
from .errors import WorkflowDescriptionError

logger = logging.getLogger(__name__)

'''
User configuration settings

Describe the experimental layout (directory structure and filename nomenclature)
by Python format strings. The fieldnames are replaced by the program with the
values of configuration class attributes.
'''
#: Format string for the generation of a full path to the user configuration settings file.
USER_CFG_FILE_FORMAT = '{experiment_dir}{sep}user.cfg.yml'

#: Format string for building default layer names based on time point, channel, and z-plane index.
LAYER_NAME_FORMAT = 't{t:0>3}_c{c:0>3}_z{z:0>3}'

#: Format string for building image filenames based on plate name, time point index, well name,
#: y and x coordinates of the image within the well, channel index and z-plane index.
IMAGE_NAME_FORMAT = '{plate_name}_t{t:0>3}_{w}_y{y:0>3}_x{x:0>3}_c{c:0>3}_z{z:0>3}.png'


def check_stage_name(stage_name):
    '''
    Check whether a described stage is known.

    Parameters
    ----------
    stage_name: str
        name of the stage

    Raises
    ------
    tmlib.errors.WorkflowDescriptionError
        when `stage_name` is unknown

    See also
    --------
    :py:const:`tmlib.tmaps.canonical.STAGES`
    '''
    known_names = canonical.STAGES
    if stage_name not in known_names:
        raise WorkflowDescriptionError(
                'Unknown stage "%s". Known stages are: "%s"'
                % (stage_name, '", "'.join(known_names)))


def check_step_name(step_name, stage_name=None):
    '''
    Check whether a described step is known.

    Parameters
    ----------
    step_name: str
        name of the step
    stage_name: str, optional
        name of the corresponding stage

    Raises
    ------
    tmlib.errors.WorkflowDescriptionError
        when `step_name` is unknown or when step with name `step_name` is not
        part of stage with name `stage_name`

    Note
    ----
    When `stage_name` is provided, it is also checked whether `step_name` is a
    valid step within stage named `stage_name`.

    See also
    --------
    :py:const:`tmlib.tmaps.canonical.STEPS_PER_STAGE`
    '''
    if stage_name:
        known_names = canonical.STEPS_PER_STAGE[stage_name]
        if step_name not in known_names:
            raise WorkflowDescriptionError(
                    'Unknown step "%s" for stage "%s". Known steps are: "%s"'
                    % (step_name, stage_name, '", "'.join(known_names)))
    else:
        known_names = utils.flatten(canonical.STEPS_PER_STAGE.values())
        if step_name not in known_names:
            raise WorkflowDescriptionError(
                    'Unknown step "%s". Known steps are: "%s"'
                    % (step_name, '", "'.join(known_names)))


class WorkflowDescription(object):

    '''
    Description of a TissueMAPS processing workflow.

    A workflow consists of *stages*, which themselves are made up of *steps*.

    Each *step* is a collection of individual tasks, which can be processed
    in parallel on a computer cluster.

    The workflow is described by a mapping of key-value pairs::

        mapping = {
            "workflow":
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

    A WorkflowDescription can be constructed from a dictionary and converted
    back into a dictionary::

        >>>obj = WorkflowDescription(mapping)
        >>>dict(obj)

    See also
    --------
    :py:class:`tmlib.tmaps.descriptions.WorkflowStageDescription`
    :py:class:`tmlib.tmaps.descriptions.WorkflowStepDescription`
    '''

    _PERSISTENT_ATTRS = {
        'stages', 'verbosity', 'virtualenv'
    }

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class WorkflowDescription.

        Parameters
        ----------
        **kwargs: dict, optional
            description of a workflow

        Returns
        -------
        tmlib.tmaps.description.WorkflowDescription

        Raises
        ------
        KeyError
            when `kwargs` doesn't have key "stages"
        '''
        # Set defaults
        self.virtualenv = None
        self.verbosity = 1
        # Check stage description
        if 'stages' not in kwargs:
            raise KeyError('Argument "kwargs" must have key "stages".')
        for k in kwargs.keys():
            if k not in self._PERSISTENT_ATTRS:
                raise ValueError('Unknown workflow descriptor: "%s"' % k)
        self.stages = list()
        stage_names = list()
        for stage in kwargs['stages']:
            name = stage['name']
            check_stage_name(name)
            stage_dependencies = canonical.INTER_STAGE_DEPENDENCIES[name]
            for dep in stage_dependencies:
                if dep not in stage_names:
                    raise WorkflowDescriptionError(
                            'Stage "%s" requires upstream stage "%s"'
                            % (name, dep))
            for step in stage['steps']:
                check_step_name(step['name'], name)
            stage_names.append(name)
            self.stages.append(WorkflowStageDescription(**stage))

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

    @property
    def verbosity(self):
        '''
        Returns
        -------
        int
            logging verbosity level (default: ``1``)

        See also
        --------
        :py:const:`tmlib.logging_utils.VERBOSITY_TO_LEVELS`
        '''
        return self._verbosity

    @verbosity.setter
    def verbosity(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "verbosity" must have type int.')
        if value < 0:
            raise ValueError('Attribute "verbosity" must be positive.')
        if value > len(logging_utils.VERBOSITY_TO_LEVELS):
            logging.warning('verbosity exceeds maximally possible level')
        self._verbosity = value

    def __iter__(self):
        for attr in vars(self):
            if attr in self._PERSISTENT_ATTRS:
                if attr == 'stages':
                    yield (attr, [dict(s) for s in getattr(self, attr)])
                else:
                    yield (attr, getattr(self, attr))


class WorkflowStageDescription(object):

    '''
    Description of a TissueMAPS workflow stage.
    '''

    _PERSISTENT_ATTRS = {'name', 'steps'}

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class WorkflowStageDescription.

        Parameters
        ----------
        **kwargs: dict, optional
            description of a workflow stage

        Returns
        -------
        tmlib.tmaps.description.WorkflowStageDescription

        Raises
        ------
        KeyError
            when `kwargs` doesn't have the keys "name" and "steps"
        '''
        for k in self._PERSISTENT_ATTRS:
            if k not in kwargs:
                raise KeyError('Argument "kwargs" must have key "%s".' % k)
        self.name = kwargs['name']
        check_stage_name(self.name)
        if not kwargs['steps']:
            raise ValueError(
                'Value of "steps" of argument "kwargs" cannot be empty.')
        self.steps = list()
        step_names = list()
        for step in kwargs['steps']:
            name = step['name']
            check_step_name(name)
            # Ensure that dependencies between steps within the stage
            # are fulfilled
            if name in canonical.INTRA_STAGE_DEPENDENCIES:
                for dep in canonical.INTRA_STAGE_DEPENDENCIES[name]:
                    if dep not in step_names:
                        raise WorkflowDescriptionError(
                                'Step "%s" requires upstream step "%s"'
                                % (name, dep))
            step_names.append(name)
            self.steps.append(WorkflowStepDescription(**step))

    @property
    def name(self):
        '''
        Returns
        -------
        str
            name of the stage

        Note
        ----
        Must correspond to a name of a `tmlib` command line program
        (subpackage).
        '''
        return self._name

    @name.setter
    def name(self, value):
        if not isinstance(value, basestring):
            raise TypeError('Attribute "name" must have type basestring')
        self._name = str(value)

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

    def __iter__(self):
        yield ('name', getattr(self, 'name'))
        yield ('steps', [dict(s) for s in getattr(self, 'steps')])


class WorkflowStepDescription(object):

    '''
    Description of a step as part of a TissueMAPS workflow stage.
    '''

    _PERSISTENT_ATTRS = {'name', 'args'}

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class WorkflowStep.

        Parameters
        ----------
        **kwargs: dict, optional
            description of a step of a workflow stage

        Returns
        -------
        tmlib.tmaps.description.WorkflowStepDescription

        Raises
        ------
        TypeError
            when `description` doesn't have type dict
        KeyError
            when `description` doesn't have keys "name" and "args"
        '''
        for attr in self._PERSISTENT_ATTRS:
            if attr not in kwargs:
                raise KeyError('Argument "kwargs" requires key "%s"')
        self.name = kwargs['name']
        args_handler = workflow.load_method_args('init')
        self.args = args_handler()
        try:
            variable_args_handler = workflow.load_var_method_args(
                                        self.name, 'init')
        except ImportError:
            raise WorkflowDescriptionError(
                    'Step "%s" doesn\'t exist.' % self.name)
        if kwargs['args']:
            self.args.variable_args = variable_args_handler(**kwargs['args'])
            for arg in kwargs['args']:
                if arg not in self.args.variable_args._persistent_attrs:
                    raise WorkflowDescriptionError(
                            'Unknown argument "%s" for step "%s".'
                            % (arg, self.name))
        else:
            self.args.variable_args = variable_args_handler()

    @property
    def name(self):
        '''
        Returns
        -------
        str
            name of the step

        Note
        ----
        Must correspond to a name of a `tmaps` command line program
        (a `tmlib` subpackage).
        '''
        return self._name

    @name.setter
    def name(self, value):
        if not isinstance(value, basestring):
            raise TypeError('Attribute "name" must have type basestring')
        self._name = str(value)

    @property
    def args(self):
        '''
        Returns
        -------
        tmlib.args.GeneralArgs
            arguments required by the step (i.e. arguments that can be parsed
            to the `init` method of the program-specific implementation of
            the :py:class:`tmlib.cli.CommandLineInterface` base class)

        Note
        ----
        Default values defined by the program-specific implementation of the
        `Args` class will be used in case an optional argument is not
        provided.
        '''
        return self._args

    @args.setter
    def args(self, value):
        if not isinstance(value, GeneralArgs):
            raise TypeError('Attribute "args" must have type tmlib.args.GeneralArgs')
        self._args = value

    def __iter__(self):
        yield ('name', getattr(self, 'name'))
        yield ('args', dict(getattr(self, 'args')))


class UserConfiguration(object):

    '''
    Class for experiment-specific configuration settings provided by the user.
    '''

    _PERSISTENT_ATTRS = {
        'sources_dir', 'plates_dir', 'layers_dir', 'plate_format', 'workflow'
    }

    def __init__(self, experiment_dir, cfg_settings):
        '''
        Initialize an instance of class UserConfiguration.

        Parameters
        ----------
        experiment_dir: str
            absolute path to experiment directory
        cfg_settings: dict
            user configuration settings as key-value pairs

        Raises
        ------
        OSError
            when `experiment_dir` does not exist

        Returns
        -------
        tmlib.cfg.UserConfiguration
            experiment-specific user configuration object
        '''
        self.experiment_dir = experiment_dir
        if not os.path.exists(self.experiment_dir):
            raise OSError('Experiment directory does not exist')
        self._sources_dir = None
        self._plates_dir = None
        self._layers_dir = None
        for k, v in cfg_settings.iteritems():
            if k in self._PERSISTENT_ATTRS:
                if k == 'workflow':
                    v = WorkflowDescription(**v)
                setattr(self, k, v)

    @property
    def sources_dir(self):
        '''
        Returns
        -------
        str
            absolute path to the directory where source files are located

        Note
        ----
        Defaults to "sources" subdirectory of the experiment directory if not
        set.

        See also
        --------
        :py:class:`tmlib.source.PlateSource`
        :py:class:`tmlib.source.PlateAcquisition`
        '''
        if self._sources_dir is None:
            self._sources_dir = os.path.join(self.experiment_dir, 'sources')
            logger.debug('set default "sources" directory: %s',
                         self._sources_dir)
        return self._sources_dir

    @sources_dir.setter
    def sources_dir(self, value):
        if not(isinstance(value, basestring) or value is None):
            raise TypeError('Attribute "plates_dir" must have type str')
        if value is None:
            self._sources_dir = None
        else:
            self._sources_dir = str(value)

    @property
    def plates_dir(self):
        '''
        Returns
        -------
        str
            absolute path to the directory where extracted files are located
            (grouped per *plate*)

        Note
        ----
        Defaults to "plates" subdirectory of the experiment directory if not
        set.

        See also
        --------
        :py:class:`tmlib.plate.Plate`
        :py:class:`tmlib.cycle.Cycle`
        '''
        if self._plates_dir is None:
            self._plates_dir = os.path.join(self.experiment_dir, 'plates')
            logger.debug('set default "plates" directory: %s',
                         self._plates_dir)
        return self._plates_dir

    @plates_dir.setter
    def plates_dir(self, value):
        if not(isinstance(value, basestring) or value is None):
            raise TypeError('Attribute "plates_dir" must have type str')
        if value is None:
            self._plates_dir = None
        else:
            self._plates_dir = str(value)

    @property
    def layers_dir(self):
        '''
        Returns
        -------
        str
            absolute path to the directory where image pyramids and associated
            data are stored

        Note
        ----
        Defaults to "layers" subdirectory of the experiment directory if
        not set.

        See also
        --------
        :py:mod:`tmlib.illuminati.layers`
        '''
        if self._layers_dir is None:
            self._layers_dir = os.path.join(self.experiment_dir, 'layers')
            logger.debug('set default "layers" directory: %s',
                         self._layers_dir)
        return self._layers_dir

    @layers_dir.setter
    def layers_dir(self, value):
        if not(isinstance(value, basestring) or value is None):
            raise TypeError('Attribute "layers_dir" must have type str')
        if value is None:
            self._layers_dir = None
        else:
            self._layers_dir = str(value)

    @property
    def plate_format(self):
        '''
        Returns
        -------
        int
            plate format, i.e. total number of wells per plate
        '''
        return self._plate_format

    @plate_format.setter
    def plate_format(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "plate_format" must have type int')
        if value not in Plate.SUPPORTED_PLATE_FORMATS:
            raise ValueError(
                    'Attribute "plate_format" can be set to "%s"'
                    % '"or "'.join(Plate.SUPPORTED_PLATE_FORMATS))
        self._plate_format = value

    @property
    def workflow(self):
        '''
        Returns
        -------
        tmlib.tmaps.workflow.WorkflowDescription
            description of the workflow that should be processed on the cluster
        '''
        return self._workflow

    @workflow.setter
    def workflow(self, value):
        if not isinstance(value, WorkflowDescription):
            raise TypeError(
                'Attribute "workflow" must have type WorkflowDescription')
        self._workflow = value

    def __iter__(self):
        for attr in dir(self):
            if attr in self._PERSISTENT_ATTRS:
                if not hasattr(self, attr):
                    raise AttributeError(
                            '"%s" object has no attribute "%s"'
                            % (self.__class__.__name__, attr))
                value = getattr(self, attr)
                if attr == 'workflow':
                    value = dict(value)
                yield (attr, value)

    @property
    def cfg_file(self):
        '''
        Returns
        -------
        str
            absolute path to the configuration file
        '''
        return USER_CFG_FILE_FORMAT.format(
                    experiment_dir=self.experiment_dir, sep=os.path.sep)

    def dump_to_file(self):
        '''
        Convert the object to a mapping and write to a YAML file.

        See also
        --------
        :py:const:`tmlib.cfg.USER_CFG_FILE_FORMAT`
        '''
        with YamlWriter() as writer:
            writer.write(self.cfg_file, dict(self))
