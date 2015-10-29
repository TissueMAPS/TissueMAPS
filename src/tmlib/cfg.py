import os
import logging
from .plate import Plate

logger = logging.getLogger(__name__)

'''
Configuration settings constants:

Describe the experimental layout (directory structure and filename nomenclature)
by Python format strings. The fieldnames are replaced by the program with the
values of configuration class attributes.
'''

USER_CFG_FILE_FORMAT = '{experiment_dir}{sep}user.cfg.yml'

LAYER_NAME_FORMAT = 't{t:0>3}_c{c:0>3}_z{z:0>3}'

IMAGE_NAME_FORMAT = '{plate_name}_t{t:0>3}_{w}_y{y:0>3}_x{x:0>3}_c{c:0>3}_z{z:0>3}.png'


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
    :mod:`tmlib.tmaps.descriptions.WorkflowStageDescription`
    :mod:`tmlib.tmaps.descriptions.WorkflowStepDescription`
    '''

    def __init__(self, description):
        '''
        Initialize an instance of class WorkflowDescription.

        Parameters
        ----------
        description: dict, optional
            description of a workflow

        Returns
        -------
        tmlib.tmaps.description.WorkflowDescription

        Raises
        ------
        TypeError
            when `description` doesn't have type dict
        KeyError
            when `description` doesn't have key "stages"
        '''
        if not isinstance(description, dict):
            raise TypeError('Argument "description" must have type dict.')
        if 'stages' not in description:
            raise KeyError('Argument "description" must have key "stages".')
        self.stages = [
            WorkflowStageDescription(s) for s in description['stages']
        ]

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

    def __iter__(self):
        yield ('stages', [dict(s) for s in getattr(self, 'stages')])


class WorkflowStageDescription(object):

    '''
    Description of a TissueMAPS workflow stage.
    '''

    def __init__(self, description=None):
        '''
        Initialize an instance of class WorkflowStageDescription.

        Parameters
        ----------
        description: dict, optional
            description of a workflow stage

        Returns
        -------
        tmlib.tmaps.description.WorkflowStageDescription

        Raises
        ------
        TypeError
            when `description` doesn't have type dict
        KeyError
            when `description` doesn't have the keys "name" and "steps"
        '''
        if not isinstance(description, dict):
            raise TypeError('Argument "description" must have type dict.')
        if not('name' in description and 'steps' in description):
            raise KeyError(
                'Argument "description" must have keys "name" and "steps".')
        self.name = description['name']
        if not description['steps']:
            raise ValueError(
                'Value of "steps" of argument "description" cannot be empty.')
        self.steps = [
            WorkflowStepDescription(s) for s in description['steps']
        ]

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

    def __init__(self, description=None):
        '''
        Initialize an instance of class WorkflowStep.

        Parameters
        ----------
        description: dict, optional
            description of a step of a workflow stage

        Returns
        -------
        tmlib.tmaps.description.WorkflowStepDescription

        Raises
        ------
        TypeError
            when `description` doesn't have type dict
        KeyError
            when `description` doesn't have the keys "name" and "args"
        '''
        if not('name' in description and 'args' in description):
            raise KeyError(
                    'Argument "description" requires keys "name" and "args"')
        self.name = description['name']
        self.args = description['args']

    @property
    def name(self):
        '''
        Returns
        -------
        str
            name of the step

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
    def args(self):
        '''
        Returns
        -------
        dict
            arguments required by the step (arguments that can be parsed
            to the "init" method of the corresponding *cli* class)

        Note
        ----
        Default values defined by the corresponding *init* subparser will
        be used in case an optional argument is not provided.

        See also
        --------
        `tmlib.cli`_
        '''
        return self._args

    @args.setter
    def args(self, value):
        if not(isinstance(value, dict) or value is None):
            raise TypeError('Attribute "args" must have type dict')
        if value is not None:
            if not all([isinstance(k, basestring) for k, v in value.iteritems()]):
                raise TypeError('Keys of "args" must have type basestring.')
            if any([v is None for k, v in value.iteritems()]):
                raise ValueError('Values of "args" must be specified.')
        self._args = value

    def __iter__(self):
        yield ('name', getattr(self, 'name'))
        yield ('args', getattr(self, 'args'))


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
                    v = WorkflowDescription(v)
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
        :mod:`tmlib.source.PlateSource`
        :mod:`tmlib.source.PlateAcquisition`
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
        :mod:`tmlib.plate.Plate`
        :mod:`tmlib.cycle.Cycle`
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
        :mod:`tmlib.illuminati.layers`
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
