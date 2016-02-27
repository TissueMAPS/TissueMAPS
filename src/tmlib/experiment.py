import re
import os
import logging
import numpy as np
from natsort import natsorted
from cached_property import cached_property
from collections import defaultdict
from . import cfg
from . import utils
from .plate import Plate
from .source import PlateSource
from .metadata import ChannelLayerMetadata
from .errors import NotSupportedError
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
    :py:class:`tmlib.plate.Plate`
    :py:class:`tmlib.cycle.Cycle`
    '''

    def __init__(self, experiment_dir, user_cfg=None, library='numpy'):
        '''
        Initialize an instance of class Experiment.

        Parameters
        ----------
        experiment_dir: str
            absolute path to the experiment root folder
        user_cfg: tmlib.cfg.UserConfiguration, optional
            user configuration settings (default: ``None``)
        library: str, optional
            image library that should be used
            (options: ``"vips"`` or ``"numpy"``, default: ``"numpy"``)

        Raises
        ------
        OSError
            when `experiment_dir` does not exist or when `user_cfg` is ``None``
            and user configuration file does not exist
        ValueError
            when `library` is not specified correctly

        Note
        ----
        When no user configuration settings are provided, the program tries
        to read them from a file.

        See also
        --------
        :py:class:`tmlib.cfg.UserConfiguration`
        '''
        self.experiment_dir = os.path.expandvars(experiment_dir)
        self.experiment_dir = os.path.expanduser(self.experiment_dir)
        self.experiment_dir = os.path.abspath(self.experiment_dir)
        if not os.path.exists(self.experiment_dir):
            raise OSError('Experiment directory does not exist')
        self.library = library
        if self.library not in {'vips', 'numpy'}:
            raise ValueError(
                    'Argument "library" must be either "numpy" or "vips"')
        self.user_cfg = user_cfg
        if user_cfg is None:
            if not os.path.exists(self.user_cfg_file):
                raise OSError(
                        'User configuration settings file does not exist: %s'
                        % self.user_cfg_file)

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

        Note
        ----
        Defaults to the folder name when not provided by the user.

        See also
        --------
        :py:attr:`tmlib.cfg.UserConfiguration.experiment_name`
        '''
        if self.user_cfg.experiment_name is None:
            return os.path.basename(self.dir)
        else:
            return self.user_cfg.experiment_name

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

    @property
    def user_cfg(self):
        '''
        Returns
        -------
        tmlib.cfg.UserConfiguration
            experiment-specific user configuration settings

        Note
        ----
        If not set, the settings are loaded from a configuration file.
        Its location is specified by the `user_cfg_file` attribute.

        Raises
        ------
        OSError
            when value is ``None`` and configuration settings file does not
            exist
        '''
        if self._user_cfg is None:
            logger.debug('loading user configuration settings from file: %s',
                         self.user_cfg_file)
            if not os.path.exists(self.user_cfg_file):
                raise OSError(
                    'User configuration settings file does not exist: %s'
                    % self.user_cfg_file)
            with YamlReader() as reader:
                config_settings = reader.read(self.user_cfg_file)
                if not config_settings:
                    raise ValueError('No user configuration provided.')
            self._user_cfg = cfg.UserConfiguration(self.dir, **config_settings)
        return self._user_cfg

    @user_cfg.setter
    def user_cfg(self, value):
        if not(isinstance(value, cfg.UserConfiguration) or value is None):
            raise TypeError(
                    'Attribute "user_cfg" must have type UserConfiguration')
        # Update configuration on disk to make it persistent, otherwise
        # this would create inconsistencies in workflows.
        # if value:
            # value.dump_to_file()
        self._user_cfg = value

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
        Directory is created if it doesn't exist.
        '''
        plates_dir = self.user_cfg.plates_dir
        if not os.path.exists(plates_dir):
            logger.debug('create directory for plates: %s', plates_dir)
            os.mkdir(plates_dir)
        return plates_dir

    def _is_plate_dir(self, folder):
        format_string = Plate.PLATE_DIR_FORMAT
        regexp = utils.regex_from_format_string(format_string)
        return True if re.match(regexp, folder) else False

    @cached_property
    def plates(self):
        '''
        Returns
        -------
        List[tmlib.plate.Plate]
            configured plate objects
        '''
        plate_dirs = [
            os.path.join(self.plates_dir, d)
            for d in os.listdir(self.plates_dir)
            if os.path.isdir(os.path.join(self.plates_dir, d)) and
            self._is_plate_dir(d)
        ]
        plate_dirs = natsorted(plate_dirs)
        return [
            Plate(d, self.user_cfg.plate_format, self.library)
            for d in plate_dirs
        ]

    def add_plate(self):
        '''
        Add a plate to the experiment, i.e. create a subdirectory in
        `plates_dir`.

        Returns
        -------
        Plate
            configured plate object

        Raises
        ------
        OSError
            when the plate already exists
        '''
        new_plate_index = len(self.plates) - 1
        new_plate_folder = Plate.PLATE_DIR_FORMAT.format(index=new_plate_index)
        new_plate_dir = os.path.join(self.plates_dir, new_plate_folder)
        if os.path.exists(new_plate_dir):
            raise OSError('Plate directory already exists: %s' % new_plate_dir)
        logger.info('add plate #%d', new_plate_index)
        os.mkdir(new_plate_dir)
        new_plate = Plate(new_plate_dir,
                          self.user_cfg.plate_format, self.library)
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

        Note
        ----
        Directory is created if it doesn't exist.
        '''
        sources_dir = self.user_cfg.sources_dir
        if not os.path.exists(sources_dir):
            logger.debug('create directory for sources: %s', sources_dir)
            os.mkdir(sources_dir)
        return sources_dir

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
        List[tmlib.source.PlateSource]
            configured plate acquisitions objects

        See also
        --------
        :py:class:`tmlib.source.PlateSource`

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
            if os.path.isdir(os.path.join(self.sources_dir, d)) and
            self._is_plate_source_dir(d)
        ])
        return [
            PlateSource(d, self.user_cfg.acquisition_mode)
            for d in plate_source_dirs
        ]

    @cached_property
    def layers_dir(self):
        '''
        Returns
        -------
        str
            absolute path to the folder holding the layers
            (image pyramids and associated data)

        Note
        ----
        Directory is created if it doesn't exist.

        See also
        --------
        :py:mod:`tmlib.illuminati`
        '''
        layers_dir = self.user_cfg.layers_dir
        if not os.path.exists(layers_dir):
            logger.debug('create directory for layers: %s', layers_dir)
            os.mkdir(layers_dir)
        return layers_dir

    @cached_property
    def layer_names(self):
        '''
        Returns
        -------
        Dict[tuple, str]
            names of layers for each combination of time point, channel,
            and z-plane
        '''
        names = dict()
        for plate in self.plates:
            for cycle in plate.cycles:
                t = cycle.index
                md = cycle.image_metadata
                channels = np.unique(md['channel_ix'])
                zplanes = np.unique(md['zplane_ix'])
                for c in channels:
                    for z in zplanes:
                        names[(t, c, z)] = cfg.LAYER_NAME_FORMAT.format(
                                                    t=t, c=c, z=z)
        return names

    @property
    def layer_metadata(self):
        '''
        Returns
        -------
        Dict[str, tmlib.metadata.ChannelLayerMetadata]
            metadata for each layer
        '''
        # TODO: make more efficient (e.g. pandas.DataFrame)
        layer_metadata = dict()
        for plate in self.plates:
            for cycle in plate.cycles:
                md = cycle.image_metadata
                for indentifier, name in self.layer_names.items():
                    if indentifier[0] != cycle.index:
                        continue
                    c = indentifier[1]
                    z = indentifier[2]
                    metadata = ChannelLayerMetadata()
                    metadata.name = name
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
                    layer_metadata[name] = metadata
        return layer_metadata

    # @cached_property
    # def visual_layers_map(self):
    #     '''
    #     Returns
    #     -------
    #     Dict[str, List[str]]
    #         layer names for each visual

    #     Note
    #     ----
    #     A `visual` is an abstract group of `layers`, which are visualized
    #     together. In the simplest case of a 2D dataset, each `visual` maps to
    #     only one `layer`, but there are other scenarios:
    #         * 3D dataset with multiple focal planes:
    #           1 `visual` -> *n* `layers`
    #         * Time series dataset with multiple time points:
    #           1 `visual` -> *n*x*m* `layers`
    #         * Multiplexing dataset with multiple time points:
    #           1 `visual` -> *n* `layer`
    #     where *n* is the number of focal planes and *m* is the number of
    #     time points.
    #     '''
    #     if hasattr(self.user_cfg, 'visuals'):
    #         # TODO: allow user to give visuals more meaningful names,
    #         # such as "DAPI" instead of "t000_c000"
    #         raise NotSupportedError('Functionality not yet supported.')
    #     mode = self.user_cfg.acquisition_mode
    #     names = defaultdict(list)
    #     for plate in self.plates:
    #         for cycle in plate.cycles:
    #             t = cycle.index
    #             md = cycle.image_metadata
    #             channels = np.unique(md['channel_ix'])
    #             zplanes = np.unique(md['zplane_ix'])
    #             for c in channels:
    #                 for z in zplanes:
    #                     v_name = cfg.VISUAL_NAME_FORMAT[mode].format(t=t, c=c)
    #                     names[v_name].append(self.layer_names[(t, c, z)])
    #     return names

    # @property
    # def visual_names(self):
    #     '''
    #     Returns
    #     -------
    #     List[str]
    #         names of the visuals
    #     '''
    #     return self.visual_layers_map.keys()

    @property
    def data_file(self):
        '''
        Returns
        -------
        str
            name of the HDF5 file holding the measurement datasets,
            i.e. the results of an image analysis pipeline such as
            segmentations and features for the segmented objects

        See also
        --------
        :py:class:`tmlib.layer.ObjectLayer`
        '''
        return 'data.h5'

    def get_image_by_name(self, name):
        '''
        Retrieve an image object for a given name.

        Parameters
        ----------
        name: str
            name of the image

        Returns
        -------
        tmlib.image.ChannelImage
            corresponding image object

        Raises
        ------
        tmlibs.errors.MetadataError
            when no or more than one image are found for `name`
        '''
        for plate in self.plates:
            for cycle in plate.cycles:
                md = cycle.image_metadata
                ix = md[md.name == name].index
                if len(ix) > 1:
                    raise MetadataError('Image names must be unique.')
                elif len(ix) == 1:
                    return cycle.get_image_subset(ix)[0]
        raise MetadataError('There is no image with name "%s"' % name)
