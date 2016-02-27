'''
User configuration settings

Describe the experimental layout (directory structure and filename nomenclature)
by Python format strings. The fieldnames are replaced by the program with the
values of configuration class attributes.
'''
import os
import logging
import importlib
from .plate import Plate
from .writers import YamlWriter
from .errors import WorkflowDescriptionError
from .tmaps.description import WorkflowDescription

logger = logging.getLogger(__name__)

#: Format string for building the full path to the user configuration
#: settings file.
USER_CFG_FILE_FORMAT = '{experiment_dir}{sep}user.cfg.yml'

#: Format string for building default layer names.
LAYER_NAME_FORMAT = 't{t:0>3}_c{c:0>3}_z{z:0>3}'

#: Format string for each acquisition mode for building visual names.
VISUAL_NAME_FORMAT = {
    'multiplexing': 't{t:0>3}_c{c:0>3}',
    'series': 'c{c:0>3}',
}

#: Format string for building image filenames.
IMAGE_NAME_FORMAT = 'p{p:0>2}_t{t:0>3}_{w}_y{y:0>3}_x{x:0>3}_c{c:0>3}_z{z:0>3}.tif'


class UserConfiguration(object):

    '''
    Class for experiment-specific configuration settings provided by the user.
    '''

    _PERSISTENT_ATTRS = {
        'sources_dir', 'plates_dir', 'layers_dir', 'plate_format', 'workflow'
    }

    def __init__(self, experiment_dir, plate_format, experiment_name=None,
                 plate_names=None,
                 acquisition_mode='multiplexing',
                 sources_dir=None, plates_dir=None, layers_dir=None, **kwargs):
        '''
        Initialize an instance of class UserConfiguration.

        Parameters
        ----------
        experiment_dir: str
            absolute path to experiment directory
        plate_format: int
            number of wells per plate
        experiment_name: str, optional
            name of the experiment (default: ``None``)
        plate_names: List[str]
            names of plates belonging to the experiment (default: ``None``)
        acquisition_mode: str, optional
            either ``"series"`` or ``"multiplexing"`` to indicate whether
            images acquired at different time points relate to the same marker
            or a different one (default: ``"multiplexing"``) 
        sources_dir: str, optional
            absolute path to the directory, where source files are located
        plates_dir: str, optional
            absolute path to the directory, where image files are located
        layers_dir: str, optional
            absolute path to the directory, where layers are located
        **kwargs: dict
            optional configuration settings arguments as key-value pairs

        Raises
        ------
        OSError
            when `experiment_dir` does not exist
        WorkflowDescriptionError
            when `kwargs` contains an incorrect "workflow" description
        '''
        self.experiment_dir = experiment_dir
        if not os.path.exists(self.experiment_dir):
            raise OSError('Experiment directory does not exist')
        self.experiment_name = experiment_name
        self.plate_names = plate_names
        self.plate_format = plate_format
        self.acquisition_mode = acquisition_mode
        self._sources_dir = sources_dir
        self._plates_dir = plates_dir
        self._layers_dir = layers_dir
        self._workflow = None
        for k, v in kwargs.iteritems():
            if k in self._PERSISTENT_ATTRS:
                if k == 'workflow':
                    if v is None:
                        continue
                    workflow_type = v.get('type', None)
                    if workflow_type is None:
                        raise WorkflowDescriptionError(
                                'Workflow requires key "type".')
                    module_name = 'tmlib.tmaps.%s' % workflow_type
                    try:
                        module = importlib.import_module(module_name)
                    except ImportError:
                        raise WorkflowDescriptionError(
                                'Workflow "type" is unknown.')
                    class_name = \
                        '%sWorkflowDescription' % workflow_type.capitalize()
                    try:
                        class_instance = getattr(module, class_name)
                    except AttributeError:
                        raise WorkflowDescriptionError(
                                'Workflow "type" is not implemented.')
                    v.pop('type')
                    v = class_instance(**v)
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
    def experiment_name(self):
        '''
        Returns
        -------
        str
            name of the experiment
        '''
        return self._experiment_name

    @experiment_name.setter
    def experiment_name(self, value):
        if not(isinstance(value, basestring) or value is None):
            raise TypeError(
                    'Attribute "experiment_name" must have type basestring')
        self._experiment_name = value

    @property
    def plate_format(self):
        '''
        Returns
        -------
        int
            total number of wells per plate
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
    def plate_names(self):
        '''
        Returns
        -------
        List[str]
            names of the plates belonging to the experiment
        '''
        return self._plate_names

    @plate_names.setter
    def plate_names(self, value):
        if value is not None:
            if not isinstance(value, list):
                raise TypeError('Attribute "plate_names" must have type list')
            if not all([isinstance(v, basestring) for v in value]):
                raise TypeError(
                        'Elements of attribute "plate_names" must have '
                        'type basestring')
        self._plate_names = value

    @property
    def acquisition_mode(self):
        '''
        Returns
        -------
        str
            acquisition mode, i.e. whether separate acquisitions relate to the
            same marker as part of a time series experiment or another marker
            as part of a multiplexing experiment
            (options: ``{"series", "multiplexing"}``,
             default: ``"multiplexing"``)
        '''
        return self._acquisition_mode

    @acquisition_mode.setter
    def acquisition_mode(self, value):
        if not isinstance(value, basestring):
            raise TypeError(
                'Attribute "dimensionality" must have type basestring')
        if value not in {'series', 'multiplexing'}:
            # TODO: ignore case
            raise ValueError(
                'Attribute "dimensionality" must be either "series" '
                'or "multiplexing"')
        self._acquisition_mode = str(value)

    @property
    def workflow(self):
        '''
        Returns
        -------
        tmlib.tmaps.description.WorkflowDescription
            description of the workflow that should be processed on the cluster
        '''
        return self._workflow

    @workflow.setter
    def workflow(self, value):
        if not isinstance(value, WorkflowDescription):
            raise TypeError(
                'Attribute "workflow" must have type '
                'tmlib.tmaps.description.WorkflowDescription')
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
                    if value is not None:
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
