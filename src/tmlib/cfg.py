import os
import re
import logging
from . import utils
from .tmaps import workflow
from .tmaps import canonical
from .plate import Plate
from .args import VariableArgs
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

    Note
    ----
    The input mapping will not be identical to the output mapping, because
    default values will be added for optional arguments that are not provided.

    See also
    --------
    :py:class:`tmlib.tmaps.descriptions.WorkflowStageDescription`
    :py:class:`tmlib.tmaps.descriptions.WorkflowStepDescription`
    '''

    _PERSISTENT_ATTRS = {
        'stages', 'virtualenv'
    }

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class WorkflowDescription.

        Parameters
        ----------
        **kwargs: dict, optional
            additional workflow descriptions

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
        # Check stage description
        for k in kwargs.keys():
            if k not in self._PERSISTENT_ATTRS:
                raise WorkflowDescriptionError(
                        'Unknown workflow descriptor: "%s"' % k)
        self.stages = list()
        if kwargs:
            for stage in kwargs['stages']:
                name = stage['name']
                check_stage_name(name)
                for step in stage['steps']:
                    check_step_name(step['name'], name)
                self.add_stage(WorkflowStageDescription(**stage))

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

    def add_stage(self, stage_description):
        '''
        Add an additional stage to the workflow.

        Parameters
        ----------
        stage_description: tmlib.cfg.WorkflowStageDescription
            description of the stage that should be added

        Raises
        ------
        TypeError
            when `stage_description` doesn't have type
            :py:class:`tmlib.cfg.WorkflowStageDescription`
        '''
        if not isinstance(stage_description, WorkflowStageDescription):
            raise TypeError(
                    'Argument "stage_description" must have type '
                    'tmlib.cfg.WorkflowStageDescription.')
        name = stage_description.name
        stage_names = [s.name for s in self.stages]
        if name in canonical.INTER_STAGE_DEPENDENCIES:
            for dep in canonical.INTER_STAGE_DEPENDENCIES[name]:
                if dep not in stage_names:
                    raise WorkflowDescriptionError(
                            'Stage "%s" requires upstream stage "%s"'
                            % (name, dep))
        step_names = [s.name for s in stage_description.steps]
        required_steps = canonical.STEPS_PER_STAGE[stage_description.name]
        for name in step_names:
            if name not in required_steps:
                raise WorkflowDescriptionError(
                            'Stage "%s" requires the following steps: "%s" '
                            % '", "'.join(required_steps))
        self.stages.append(stage_description)

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

        Returns
        -------
        tmlib.tmaps.description.WorkflowStageDescription

        Raises
        ------
        KeyError
            when `kwargs` doesn't have the keys "name" and "steps"
        '''
        if steps is not None:
            if not steps:
                raise ValueError(
                    'Value of "steps" of argument "kwargs" cannot be empty.')
        if not isinstance(name, basestring):
            raise TypeError('Attribute "name" must have type basestring')
        check_stage_name(name)
        self.name = str(name)
        self.steps = list()
        if steps is not None:
            for s in steps:
                self.add_step(WorkflowStepDescription(**s))

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

    def add_step(self, step_description):
        '''
        Add an additional step to the stage.

        Parameters
        ----------
        step_description: tmlib.cfg.WorkflowStepDescription
            description of the step that should be added

        Raises
        ------
        TypeError
            when `step_description` doesn't have type
            :py:class:`tmlib.cfg.WorkflowStepDescription`
        '''
        if not isinstance(step_description, WorkflowStepDescription):
            raise TypeError(
                    'Argument "step_description" must have type '
                    'tmlib.cfg.WorkflowStepDescription.')
        name = step_description.name
        step_names = [s.name for s in self.steps]
        if name in canonical.INTRA_STAGE_DEPENDENCIES:
            for dep in canonical.INTRA_STAGE_DEPENDENCIES[name]:
                if dep not in step_names:
                    raise WorkflowDescriptionError(
                            'Step "%s" requires upstream step "%s"'
                            % (name, dep))
        self.steps.append(step_description)

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

        Returns
        -------
        tmlib.tmaps.description.WorkflowStepDescription

        Raises
        ------
        KeyError
            when `description` doesn't have keys "name" and "args"
        WorkflowDescriptionError
            when the step is not known
        '''
        if not isinstance(name, basestring):
            raise TypeError('Attribute "name" must have type basestring')
        check_step_name(name)
        self.name = str(name)
        try:
            variable_args_handler = workflow.load_var_method_args(
                                        self.name, 'init')
        except ImportError:
            raise WorkflowDescriptionError(
                    '"%s" is not a valid step name.' % self.name)
        args_handler = workflow.load_method_args('init')
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

    def __iter__(self):
        yield ('name', getattr(self, 'name'))
        # Only return the "variable_args" attribute, because these are the
        # arguments that are relevant for the workflow description
        if hasattr(self.args, 'variable_args'):
            yield ('args', dict(getattr(self.args, 'variable_args')))
        else:
            yield ('args', dict())


class UserConfiguration(object):

    '''
    Class for experiment-specific configuration settings provided by the user.
    '''

    _PERSISTENT_ATTRS = {
        'sources_dir', 'plates_dir', 'layers_dir', 'plate_format', 'workflow'
    }

    def __init__(self, experiment_dir, plate_format,
                 sources_dir=None, plates_dir=None, layers_dir=None, **kwargs):
        '''
        Initialize an instance of class UserConfiguration.

        Parameters
        ----------
        experiment_dir: str
            absolute path to experiment directory
        sources_dir: str, optional
            absolute path to the directory, where source files are located
        plates_dir: str, optional
            absolute path to the directory, where image files are located
        layers_dir: str, optional
            absolute path to the directory, where layers are located
        **kwargs: dict
            additional user configuration settings as key-value pairs

        Raises
        ------
        OSError
            when `experiment_dir` does not exist
        '''
        self.experiment_dir = experiment_dir
        if not os.path.exists(self.experiment_dir):
            raise OSError('Experiment directory does not exist')
        self.plate_format = plate_format
        self._sources_dir = sources_dir
        self._plates_dir = plates_dir
        self._layers_dir = layers_dir
        for k, v in kwargs.iteritems():
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
