import re
import os
import logging
from natsort import natsorted
from cached_property import cached_property
from . import cfg
from .readers import UserConfigurationReader
from . import utils
from .plates import WellPlate
from .plates import Slide
from .upload import Upload
from .cfg_setters import UserConfiguration
from .cfg_setters import TmlibConfiguration

logger = logging.getLogger(__name__)


class Experiment(object):
    '''
    Class for an experiment.

    An *experiment* represents a folder on disk that contains image files
    and additional data associated with the images, such as metainformation,
    measured features, segmentations, etc. The structure of the directory tree
    and the location of files is defined via format strings
    in the configuration settings file.

    An experiment consists of one or more *cycles*. A *cycle* represents a
    particular time point of image acquisition for a given sample.
    In the simplest case, there is only a single round of image acquisition.
    However, the experiment may also represent a time series,
    consisting of several iterative rounds of image acquisitions.
    In this case each *cycle* should be represented by a
    separate subfolder on disk. The names of these folders should encode the
    name of the experiment as well as the *cycle* identifier number,
    i.e. the one-based index of the time series sequence.

    See also
    --------
    `cycle.Cycle`_
    `cfg`_
    `user.cfg`_
    '''

    def __init__(self, experiment_dir, cfg=TmlibConfiguration(cfg),
                 library='vips'):
        '''
        Instantiate an instance of class Experiment.

        Parameters
        ----------
        experiment_dir: str
            absolute path to experiment folder
        cfg: TmlibConfigurations, optional
            configuration settings for names of directories and files on disk
            (default: settings provided by `cfg` module)
        library: str, optional
            image library that should be used
            (options: ``"vips"`` or ``"numpy"``, default: ``"vips"``)

        See also
        --------
        `tmlib.cfg_setters.TmlibConfiguration`_
        '''
        self.experiment_dir = os.path.expandvars(experiment_dir)
        self.experiment_dir = os.path.expanduser(self.experiment_dir)
        self.experiment_dir = os.path.abspath(self.experiment_dir)
        self.cfg = cfg
        self.library = library
        logger.debug('using the "%s" image library' % self.library)

    @property
    def user_cfg_file(self):
        '''
        Returns
        -------
        str
            absolute path to experiment-specific user configuration file
        '''
        self._user_cfg_file = self.cfg.USER_CFG_FILE.format(
                                            experiment_dir=self.dir,
                                            sep=os.path.sep)
        return self._user_cfg_file

    @cached_property
    def user_cfg(self):
        '''
        Returns
        -------
        UserConfiguration
            experiment-specific configuration settings provided by the user

        See also
        --------
        `tmlib.cfg_setters.UserConfiguration`_
        '''
        # TODO: shall we do this via the database instead?
        logger.debug('user configuration file: %s' % self.user_cfg_file)
        with UserConfigurationReader() as reader:
            configuration_settings = reader.read(self.user_cfg_file)
        self._user_cfg = UserConfiguration(configuration_settings)
        return self._user_cfg

    @property
    def name(self):
        '''
        Returns
        -------
        str
            name of the experiment
        '''
        self._name = os.path.basename(self.experiment_dir)
        return self._name

    @property
    def dir(self):
        '''
        Returns
        -------
        str
            absolute path to the experiment directory
        '''
        return self.experiment_dir

    def _is_cycle_dir(self, folder):
        regexp = utils.regex_from_format_string(self.cfg.CYCLE_DIR)
        return True if re.match(regexp, folder) else False

    @property
    def cycles(self):
        '''
        Returns
        -------
        List[WellPlate or Slide]
            configured cycle objects

        See also
        --------
        `tmlib.cycle.Cycle`_
        `tmlib.plates.WellPlate`_
        `tmlib.plates.Slide`_
        `tmlib.cfg`_
        '''
        cycle_dirs = [
            os.path.join(self.dir, d)
            for d in os.listdir(self.dir)
            if os.path.isdir(os.path.join(self.dir, d))
            and self._is_cycle_dir(d)
        ]
        cycle_dirs = natsorted(cycle_dirs)
        if not cycle_dirs:
            self._cycles = list()
            # # in this case, the *cycle* directory is the same as the
            # # the experiment directory
            # cycle_dirs = self.experiment_dir
        if self.user_cfg.WELLPLATE_FORMAT:
            self._cycles = [
                WellPlate(d, self.cfg, self.user_cfg, self.library)
                for d in cycle_dirs
            ]
        else:
            self._cycles = [
                Slide(d, self.cfg, self.user_cfg, self.library)
                for d in cycle_dirs
            ]
        return self._cycles

    @property
    def upload_dir(self):
        '''
        Returns
        -------
        str
            absolute path to the directory, where uploaded files are located
        '''
        self._upload_dir = self.cfg.UPLOAD_DIR.format(
                                            experiment_dir=self.dir,
                                            sep=os.path.sep)
        return self._upload_dir

    def _is_upload_subdir(self, folder):
        regexp = utils.regex_from_format_string(self.cfg.UPLOAD_SUBDIR)
        return True if re.match(regexp, folder) else False

    @property
    def uploads(self):
        '''
        Returns
        -------
        List[UploadContainer]
            configured upload objects

        See also
        --------
        `tmlib.upload.Upload`_
        `tmlib.cfg`_
        '''
        upload_subdirs = natsorted([
            os.path.join(self.upload_dir, d)
            for d in os.listdir(self.upload_dir)
            if os.path.isdir(os.path.join(self.upload_dir, d))
            and self._is_upload_subdir(d)
        ])
        self._uploads = [
            Upload(d, self.cfg, self.user_cfg) for d in upload_subdirs
        ]
        return self._uploads

    @property
    def reference_cycle(self):
        '''
        Returns
        -------
        str
            name of the reference cycle

        Note
        ----
        If the attribute is not set, it will be attempted to retrieve the
        information from the user configuration file. If the information is
        not available via the file, a default reference is assigned, which is
        the last cycle after sorting according to cycle names.
        '''
        if 'REFERENCE_CYCLE' in self.user_cfg.keys():
            self._reference_cycle = self.user_cfg.REFERENCE_CYCLE
            logger.debug('set reference cycle according to user configuration')
        else:
            cycle_names = natsorted([cycle.name for cycle in self.cycles])
            self._reference_cycle = cycle_names[-1]
            logger.debug('take last cycle as reference cycle')
        return self._reference_cycle

    def create_additional_cycle(self):
        '''
        Create a new cycle object and add it to the list of existing cycles.
        '''
        new_cycle_name = self.cfg.CYCLE_DIR.format(
                                            experiment=self.name,
                                            cycle_id=len(self.cycles)+1)
        logger.info('create additional cycle: %s' % new_cycle_name)
        new_cycle_dir = os.path.join(self.dir, new_cycle_name)
        logger.debug('create directory for new cycle')
        os.mkdir(new_cycle_dir)
        if self.user_cfg.WELLPLATE_FORMAT:
            new_cycle = WellPlate(new_cycle_dir, self.cfg, self.user_cfg,
                                  self.library)
        else:
            new_cycle = Slide(new_cycle_dir, self.cfg, self.user_cfg,
                              self.library)
        self.cycles.append(new_cycle)
        return new_cycle

    @cached_property
    def layers_dir(self):
        '''
        Returns
        -------
        str
            absolute path to the folder holding the layers (image pyramids)
        '''
        self._layers_dir = self.cfg.LAYERS_DIR.format(
                                            experiment_dir=self.experiment_dir,
                                            sep=os.path.sep)
        if not os.path.exists(self._layers_dir):
            logger.debug('create directory for layers pyramid directories: %s'
                         % self._layers_dir)
            os.mkdir(self._layers_dir)
        return self._layers_dir

    @property
    def data_file(self):
        '''
        Returns
        -------
        str
            absolute path to the HDF5 file holding the measurements dataset

        See also
        --------
        `dafu`_
        '''
        self._data_filename = self.cfg.DATA_FILE.format(
                                            experiment_dir=self.experiment_dir,
                                            sep=os.path.sep)
        return self._data_filename
