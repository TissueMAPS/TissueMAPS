import re
import os
import logging
import numpy as np
import collections
from natsort import natsorted
from cached_property import cached_property
from . import cfg
from . import utils
from .plate import Plate
from .source import PlateSource
from .metadata import ChannelLayerMetadata
from .metadata import ChannelMetadata
from .errors import MetadataError
from .readers import YamlReader

logger = logging.getLogger(__name__)

#: Class for hashing based on time point, channel, and z-plane.
Index = collections.namedtuple('Index', ['tpoint', 'channel', 'zplane'])


class Experiment(object):
    '''
    An *experiment* is a collection of images and associated data.

    It consists of one or more *plates*. A *plate* is a container
    for the imaged biological samples and can be associated with one or more
    *cycles*. A *cycle* represents a particular time point of image
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

    def __init__(self, experiment_dir, user_cfg=None):
        '''
        Initialize an instance of class Experiment.

        Parameters
        ----------
        experiment_dir: str
            absolute path to the experiment root folder
        user_cfg: tmlib.cfg.UserConfiguration, optional
            user configuration settings (default: ``None``)

        Raises
        ------
        OSError
            when `experiment_dir` does not exist or when `user_cfg` is ``None``
            and user configuration file does not exist

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
        self.user_cfg = user_cfg
        if user_cfg is None:
            user_cfg_file = os.path.join(self.dir, self.user_cfg_file)
            if not os.path.exists(user_cfg_file):
                raise OSError(
                        'User configuration settings file does not exist: %s'
                        % user_cfg_file)

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
        return cfg.USER_CFG_FILE_FORMAT.format()

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
            user_cfg_file = os.path.join(self.dir, self.user_cfg_file)
            logger.debug('loading user configuration settings from file: %s',
                         user_cfg_file)
            if not os.path.exists(user_cfg_file):
                raise OSError(
                    'User configuration settings file does not exist: %s'
                    % user_cfg_file)
            with YamlReader() as reader:
                config_settings = reader.read(user_cfg_file)
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

    @utils.autocreate_directory_property
    def plates_dir(self):
        '''
        Returns
        -------
        str
            absolute path to the directory, where extracted image files and
            additional metadata files are located (grouped per plate)

        Note
        ----
        Directory is autocreated if it doesn't exist.
        '''
        return self.user_cfg.plates_dir

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
        return [Plate(d, self.user_cfg.plate_format) for d in plate_dirs]

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
        new_plate = len(self.plates)
        new_plate_folder = Plate.PLATE_DIR_FORMAT.format(index=new_plate)
        new_plate_dir = os.path.join(self.plates_dir, new_plate_folder)
        if os.path.exists(new_plate_dir):
            raise OSError('Plate directory already exists: %s' % new_plate_dir)
        logger.info('add plate #%d', new_plate)
        os.mkdir(new_plate_dir)
        new_plate = Plate(new_plate_dir, self.user_cfg.plate_format)
        self.plates.append(new_plate)
        return new_plate

    @utils.autocreate_directory_property
    def sources_dir(self):
        '''
        Returns
        -------
        str
            absolute path to the directory, where source files
            (original microscope files) are located

        Note
        ----
        Directory is autocreated if it doesn't exist.
        '''
        return self.user_cfg.sources_dir

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

    @utils.autocreate_directory_property
    def layers_dir(self):
        '''
        Returns
        -------
        str
            absolute path to the folder holding the layers
            (image pyramids and associated data)

        Note
        ----
        Directory is autocreated if it doesn't exist.

        See also
        --------
        :py:mod:`tmlib.illuminati`
        '''
        return self.user_cfg.layers_dir

    @cached_property
    def layer_names(self):
        '''
        Returns
        -------
        Dict[tuple, str]
            names of layers for each combination of time point, channel,
            and z-plane index
        '''
        names = dict()
        for plate in self.plates:
            for cycle in plate.cycles:
                t = cycle.tpoint
                md = cycle.image_metadata
                channels = np.unique(md['channel'])
                zplanes = np.unique(md['zplane'])
                for c in channels:
                    for z in zplanes:
                        i = Index(t, c, z)
                        names[i] = cfg.LAYER_NAME_FORMAT.format(t=t, c=c, z=z)
        return names

    @property
    def layer_metadata(self):
        '''
        Returns
        -------
        Dict[str, tmlib.metadata.ChannelLayerMetadata]
            name and metadata of each layer
        '''
        layer_metadata = dict()
        for plate in self.plates:
            for cycle in plate.cycles:
                md = cycle.image_metadata
                for indices, name in self.layer_names.iteritems():
                    c = indices.channel
                    z = indices.zplane
                    if c not in cycle.channels:
                        continue
                    metadata = ChannelLayerMetadata()
                    metadata.name = name
                    metadata.channel = c
                    metadata.zplane = z
                    metadata.cycle = cycle.index
                    metadata.tpoint = cycle.tpoint
                    index = ((md['channel'] == c) & (md['zplane'] == z))
                    files = md[index]['name'].tolist()
                    metadata.filenames = [
                        os.path.join(cycle.image_dir, f) for f in files
                    ]
                    sites = md[index]['site'].tolist()
                    metadata.sites = sites
                    layer_metadata[name] = metadata
        return layer_metadata

    @property
    def channel_names(self):
        '''
        Returns
        -------
        List[str]
            name of each channel, the image metadata attribute `channel_index`
            can be used for indexing
        '''
        return self.channel_metadata.keys()

    @property
    def channel_metadata(self):
        '''
        Returns
        -------
        Dict[str, tmlib.metadata.ChannelMetadata]
            name and metadata of each channel
        '''
        layer_keys = np.array(self.layer_names.keys())
        channels = sorted(np.unique(layer_keys[:, 1]))
        metadata = collections.OrderedDict()  # preserve order!
        for c in channels:
            md = ChannelMetadata()
            md.name = cfg.CHANNEL_NAME_FORMAT.format(c=c)
            # We have to find out which layers belong to the channel and
            # add the corresponding metadata attributes.
            index = np.where(layer_keys[:, 1] == c)[0]
            matching_layer_keys = layer_keys[index, :]
            for index in matching_layer_keys:
                name = self.layer_names[tuple(index)]
                layer_md = self.layer_metadata[name]
                md.add_layer_metadata(layer_md)
            metadata[md.name] = md
        return metadata

    @utils.autocreate_directory_property
    def data_dir(self):
        '''
        Returns
        -------
        str
            absolute path to the folder holding the data files

        Note
        ----
        Directory is autocreated if it doesn't exist.

        See also
        --------
        :py:mod:`tmlib.jterator`
        '''
        return self.user_cfg.data_dir

    @cached_property
    def data_files(self):
        '''
        Returns
        -------
        List[str]
            names of the HDF5 files holding the measurement datasets,
            i.e. the results of an image analysis pipeline such as
            segmentations and features for the segmented objects

        See also
        --------
        :py:class:`tmlib.layer.ObjectLayer`
        '''
        files = [
            f for f in os.listdir(self.data_dir) if f.endswith('h5')
        ]
        files = natsorted(files)
        if not files:
            raise OSError('No data files found in "%s"' % self.data_dir)
        return files

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
