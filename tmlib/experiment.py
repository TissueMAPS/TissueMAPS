import re
import os
import logging
import numpy as np
from natsort import natsorted
from cached_property import cached_property
from . import cfg
from . import utils
from .plate import Plate
from .source import PlateSource
from .metadata import MosaicMetadata
from .errors import NotSupportedError
from .errors import RegexError
from .errors import MetadataError
from .readers import YamlReader

logger = logging.getLogger(__name__)


class Experiment(object):
    '''
    An *experiment* is a repository for images and associated data.

    An *experiment* consists of one or more *plates*. A *plate* is a container
    for the imaged biological samples and can be associated with one or more
    *cycles*, where a *cycle* represents a particular time point of image
    acquisition. In the simplest case, an *experiment* is composed of a single
    *plate* with only one *cycle*.
    
    The experiment and its elements are represented by directories on the
    file system and their locations are defined by the corresponding
    configuration classes.

    See also
    --------
    `tmlib.plate.Plate`_
    `tmlib.cycle.Cycle`_
    '''

    def __init__(self, experiment_dir, user_cfg=None, library='vips'):
        '''
        Initialize an instance of class Experiment.

        Parameters
        ----------
        experiment_dir: str
            absolute path to the experiment root folder
        user_cfg: UserConfiguration, optional
            user configuration settings (default: ``None``)
        library: str, optional
            image library that should be used
            (options: ``"vips"`` or ``"numpy"``)

        See also
        --------
        `tmlib.cfg`_

        Note
        ----
        When no user configuration settings are provided, the program tries
        to read them from a file.
        '''
        self.experiment_dir = os.path.expandvars(experiment_dir)
        self.experiment_dir = os.path.expanduser(self.experiment_dir)
        self.experiment_dir = os.path.abspath(self.experiment_dir)
        self.library = library
        if self.library not in {'vips', 'numpy'}:
            raise ValueError(
                    'Argument "library" must be either "numpy" or "vips"')
        self.user_cfg = user_cfg
        if self.user_cfg is None:
            logger.debug('loading user configuration settings from file: %s',
                         self.user_cfg_file)
            if not os.path.exists(self.user_cfg_file):
                raise OSError(
                    'User configuration settings file does not exist: %s'
                    % self.user_cfg_file)
            with YamlReader() as reader:
                config_settings = reader.read(self.user_cfg_file)
            self.user_cfg = cfg.UserConfiguration.set(
                                self.experiment_dir, config_settings)
        if not isinstance(self.user_cfg, cfg.UserConfiguration):
            raise TypeError(
                    'Argument "user_cfg" must have type UserConfiguration')

    @property
    def dir(self):
        '''
        Returns
        -------
        str
            absolute path to the experiment directory
        '''
        return self.experiment_dir

    @property
    def name(self):
        '''
        Returns
        -------
        str
            name of the experiment
        '''
        return os.path.basename(self.experiment_dir)

    @property
    def user_cfg_file(self):
        '''
        Returns
        -------
        str
            absolute path to an experiment-specific user configuration settings
            file
        '''
        return cfg.USER_CFG_FILE_FORMAT.format(
                    experiment_dir=self.experiment_dir, sep=os.path.sep)

    @cached_property
    def plates_dir(self):
        '''
        Returns
        -------
        str
            absolute path to the directory, where extracted image files and
            additional metadata files are located (grouped per plate)

        Note
        ----
        Creates the directory if it doesn't exist.
        '''
        self._plates_dir = self.user_cfg.plates_dir
        if not os.path.exists(self._plates_dir):
            logger.debug('create directory for plates: %s', self._plates_dir)
            os.mkdir(self._plates_dir)
        return self._plates_dir

    def _is_plate_dir(self, folder):
        format_string = Plate.PLATE_DIR_FORMAT
        regexp = utils.regex_from_format_string(format_string)
        return True if re.match(regexp, folder) else False

    @property
    def plates(self):
        '''
        Returns
        -------
        List[Plate]
            configured plate objects
        '''
        plate_dirs = [
            os.path.join(self.plates_dir, d)
            for d in os.listdir(self.plates_dir)
            if os.path.isdir(os.path.join(self.plates_dir, d))
            and self._is_plate_dir(d)
        ]
        plate_dirs = natsorted(plate_dirs)
        return [Plate(d, self.user_cfg, self.library) for d in plate_dirs]

    def add_plate(self, plate_name):
        '''
        Add a plate to the experiment, i.e. create a subdirectory in
        `plates_dir`.

        Parameters
        ----------
        plate_name: str
            name of the new plate

        Returns
        -------
        Plate
            configured plate object

        Raises
        ------
        OSError
            when the plate already exists
        '''
        new_plate_dir = Plate.PLATE_DIR_FORMAT.format(
                                plates_dir=self.plates_dir,
                                plate_name=plate_name,
                                sep=os.path.sep)
        if os.path.exists(new_plate_dir):
            raise OSError('Plate "%s" already exists.' % plate_name)
        logger.debug('add plate: %s', plate_name)
        logger.debug('create directory for plate "%s": %s',
                     plate_name, new_plate_dir)
        os.mkdir(new_plate_dir)
        new_plate = Plate(new_plate_dir, self.user_cfg, self.library)
        self.plates.append(new_plate)
        return new_plate

    @cached_property
    def sources_dir(self):
        '''
        Returns
        -------
        str
            absolute path to the directory, where source files
            (original microscope files) are located

        Raises
        ------
        OSError
            when `source_dir` does not exist

        Note
        ----
        The user has to create the directory and provide its location.
        '''
        print self.user_cfg.sources_dir
        self._sources_dir = self.user_cfg.sources_dir
        if not os.path.exists(self._sources_dir):
            raise OSError('PlateSources directory does not exist')
        return self._sources_dir

    def _is_plate_source_dir(self, folder):
        format_string = PlateSource.PLATE_SOURCE_DIR_FORMAT
        regexp = utils.regex_from_format_string(format_string)
        return True if re.match(regexp, folder) else False

    @property
    def sources(self):
        '''
        An experiment consists of one or multiple *plates*. Each *plate* itself
        is composed of one or multiple *acquisitions*, which contain the actual
        source files.

        Returns
        -------
        List[PlateSource]
            configured plate acquisitions objects

        See also
        --------
        `tmlib.source.PlateSource`_

        Note
        ----
        All *plates* belonging to one experiment must have the same layout,
        i.e. contain the same number of image acquisition sites. However, the
        number of acquired images may differ between plates, for example due to
        a different number of channels.
        '''
        plate_source_dirs = natsorted([
            os.path.join(self.sources_dir, d)
            for d in os.listdir(self.sources_dir)
            if os.path.isdir(os.path.join(self.sources_dir, d))
            and self._is_plate_source_dir(d)
        ])
        return [PlateSource(d, self.user_cfg) for d in plate_source_dirs]

    @cached_property
    def layers_dir(self):
        '''
        Returns
        -------
        str
            absolute path to the folder holding the layers
            (image pyramids and associated data)

        See also
        --------
        `tmlib.illuminati`_
        '''
        layers_dir = self.user_cfg.layers_dir
        if not os.path.exists(layers_dir):
            logger.debug('create directory for layers pyramid directories: %s'
                         % layers_dir)
            os.mkdir(layers_dir)
        return layers_dir

    @property
    def layer_metadata(self):
        '''
        Returns
        -------
        Dict[str, MosaicMetadata]
            metadata for each layer
        '''
        if hasattr(self.user_cfg, 'LAYER_NAMES'):
            raise NotSupportedError('TODO')
        self._layer_metadata = dict()
        for plate in self.plates:
            for cycle in plate.cycles:
                md = cycle.image_metadata_table
                channels = np.unique(md['channel_ix'])
                zplanes = np.unique(md['zplane_ix'])
                for c in channels:
                    for z in zplanes:
                        metadata = MosaicMetadata()
                        metadata.name = self.user_cfg.LAYER_NAME_FORMAT.format(
                                            t=cycle.index, c=c, z=z)
                        metadata.channel_ix = c
                        metadata.zplane_ix = z
                        metadata.tpoint_ix = cycle.index
                        ix = ((md['channel_ix'] == c) & (md['zplane_ix'] == z))
                        files = md[ix]['name'].tolist()
                        metadata.filenames = [
                            os.path.join(cycle.image_dir, f) for f in files
                        ]
                        sites = md[ix]['site_ix'].tolist()
                        metadata.site_ixs = sites
                        self._layer_metadata[metadata.name] = metadata
        return self._layer_metadata

    @property
    def data_file(self):
        '''
        Returns
        -------
        str
            absolute path to the HDF5 file holding the measurement datasets,
            i.e. the results of an image analysis pipeline such as
            segmentations and features for the segmented objects
        '''
        return os.path.join(self.layers_dir, 'data.h5')

    def get_image_by_name(self, name):
        '''
        Retrieve an image object for a given name.

        Parameters
        ----------
        name: str
            name of the image

        Returns
        -------
        ChannelImage
            corresponding image object
        '''
        regex = utils.regex_from_format_string(self.user_cfg.IMAGE_NAME_FORMAT)
        match = re.search(regex, os.path.basename(name))
        if not match:
            raise RegexError('Metadata could not be determined from filename')
        captures = match.groupdict()
        for plate in self.plates:
            if plate.name != captures['plate_name']:
                continue
            for cycle in plate.cycles:
                if cycle.index != int(captures['t']):
                    continue
                md = cycle.image_metadata_table
                ix = np.where(
                        (md['channel_ix'] == int(captures['c'])) &
                        (md['zplane_ix'] == int(captures['z'])) &
                        (md['well_name'] == captures['w']) &
                        (md['well_pos_x'] == int(captures['x'])) &
                        (md['well_pos_y'] == int(captures['y'])))[0]
                if len(ix) > 1:
                    raise MetadataError(
                            'A filename has to correspond to a single image.')
                return cycle.images[ix]
