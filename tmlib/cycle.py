import re
import os
import logging
import pandas as pd
from natsort import natsorted
from cached_property import cached_property
from . import utils
from .readers import ImageMetadataReader
from .image import is_image_file
from .image import ChannelImage
from .image import IllumstatsImages
from .metadata import ChannelImageMetadata
from .metadata import IllumstatsImageMetadata
from .errors import RegexpError

logger = logging.getLogger(__name__)


class Cycle(object):
    '''
    A *cycle* represents an individual image acquisition time point
    as part of a time series experiment and corresponds to a folder on disk.

    The `Cycle` class provides attributes and methods for accessing the
    contents of this folder.

    See also
    --------
    `experiment.Experiment`_
    '''

    def __init__(self, cycle_dir, cfg, user_cfg, library='vips'):
        '''
        Initialize an instance of class Cycle.

        Parameters
        ----------
        cycle_dir: str
            absolute path to the cycle directory
        cfg: TmlibConfigurations
            configuration settings for names of directories and files on disk
        user_cfg: Dict[str, str]
            additional user configuration settings
        library: str, optional
            image library that should be used
            (options: ``"vips"`` or ``"numpy"``, default: ``"vips"``)

        Raises
        ------
        OSError
            when `cycle_dir` does not exist
        '''
        self.cycle_dir = os.path.abspath(cycle_dir)
        if not os.path.exists(self.cycle_dir):
            raise OSError('Cycle directory does not exist.')
        self.cfg = cfg
        self.user_cfg = user_cfg
        self.library = library

    @property
    def name(self):
        '''
        Returns
        -------
        str
            name of the cycle folder
        '''
        self._name = os.path.basename(self.cycle_dir)
        return self._name

    @property
    def dir(self):
        '''
        Returns
        -------
        str
            absolute path to the cycle folder
        '''
        return self.cycle_dir

    @property
    def id(self):
        '''
        A *cycle* represents a time point in a time series. The identifier
        (*id*) is the one-based index of the cycle in this sequence.
        The *id* is encoded in the name of *cycle* folder name and retrieved
        from it using a regular expression.

        Returns
        -------
        int
            cycle identifier number

        Raises
        ------
        RegexpError
            when cycle identifier number cannot not be determined from folder
            name
        '''
        regexp = utils.regex_from_format_string(self.cfg.CYCLE_DIR)
        match = re.search(regexp, self.name)
        if not match:
            raise RegexpError(
                    'Can\'t determine cycle id number from folder "%s" '
                    'using format "%s" provided by the configuration settings.'
                    % (self.name, self.cfg['CYCLE_DIR']))
        self._id = int(match.group('cycle_id'))
        return self._id

    @property
    def experiment_dir(self):
        '''
        Returns
        -------
        str
            absolute path to the parent experiment directory
        '''
        self.experiment_dir = os.path.dirname(self.dir)
        return self._experiment_dir

    @property
    def experiment(self):
        '''
        Returns
        -------
        str
            name of the corresponding parent experiment folder
        '''
        self._experiment = os.path.basename(os.path.dirname(self.dir))
        return self._experiment

    @cached_property
    def image_dir(self):
        '''
        Returns
        -------
        str
            path to the folder holding the image files

        Note
        ----
        The directory is created if it doesn't exist.
        '''
        self._image_dir = self.cfg.IMAGE_DIR.format(
                                                cycle_dir=self.dir,
                                                sep=os.path.sep)
        if not os.path.exists(self._image_dir):
            logger.debug('create directory for image files: %s'
                         % self._image_dir)
            os.mkdir(self._image_dir)
        return self._image_dir

    @cached_property
    def image_files(self):
        '''
        Returns
        -------
        List[str]
            names of files in `image_dir`

        Raises
        ------
        OSError
            when no image files are found in `image_dir`

        See also
        --------
        `image.is_image_file`_
        '''
        files = [f for f in os.listdir(self.image_dir) if is_image_file(f)]
        files = natsorted(files)
        if not files:
            raise OSError('No image files found in "%s"' % self.image_dir)
        self._image_files = files
        return self._image_files

    @property
    def image_metadata_file(self):
        '''
        Returns
        -------
        str
            name of the file holding image related metadata
        '''
        self._image_metadata_file = self.cfg.IMAGE_METADATA_FILE.format(
                                            cycle_name=self.name,
                                            sep=os.path.sep)
        return self._image_metadata_file

    @cached_property
    def image_metadata(self):
        '''
        Returns
        -------
        List[ChannelImageMetadata]
            metadata for each file in `image_dir`

        Raises
        ------
        OSError
            when metadata file does not exist

        See also
        --------
        `metadata.ChannelImageMetadata`_
        '''
        metadata_file = os.path.join(self.dir, self.image_metadata_file)
        with ImageMetadataReader() as reader:
            metadata = reader.read(metadata_file)
        self._image_metadata = [
            ChannelImageMetadata.set(metadata[f])
            for f in natsorted(metadata.keys())
        ]
        return self._image_metadata

    @cached_property
    def image_metadata_table(self):
        '''
        Metadata in tabular form, where each row represents an image
        and the columns the different metadata attributes.

        Returns
        -------
        pandas.DataFrame
            metadata table
        '''
        metadata_file = os.path.join(self.dir, self.image_metadata_file)
        with ImageMetadataReader() as reader:
            metadata = reader.read(metadata_file)
        self._image_metadata_table = pd.DataFrame(metadata.values())
        return self._image_metadata_table

    @property
    def images(self):
        '''
        Returns
        -------
        List[ChannelImage]
            image object for each image file in `image_dir`

        Note
        ----
        Image objects have lazy loading functionality, i.e. the actual image
        pixel array is only loaded into memory once the corresponding attribute
        (property) is accessed.
        '''
        self._images = list()
        image_filenames = [md.name for md in self.image_metadata]
        for i, f in enumerate(image_filenames):
            img = ChannelImage.create_from_file(
                    filename=os.path.join(self.image_dir, f),
                    metadata=self.image_metadata[i],
                    library=self.library)
            self._images.append(img)
        return self._images

    @cached_property
    def stats_dir(self):
        '''
        Returns
        -------
        str
            path to the directory holding illumination statistic files

        Note
        ----
        Creates the directory if it doesn't exist.
        '''
        self._stats_dir = self.cfg.STATS_DIR.format(
                                            cycle_dir=self.dir,
                                            sep=os.path.sep)
        if not os.path.exists(self._stats_dir):
            logger.debug(
                'create directory for illumination statistics files: %s'
                % self._stats_dir)
            os.mkdir(self._stats_dir)
        return self._stats_dir

    @cached_property
    def illumstats_files(self):
        '''
        Returns
        -------
        List[str]
            names of illumination correction files in `stats_dir`

        Raises
        ------
        OSError
            when `stats_dir` does not exist or when no illumination statistic
            files are found in `stats_dir`
        '''
        stats_pattern = self.cfg.STATS_FILE.format(
                                            cycle_name=self.name,
                                            channel_id='\w+')
        stats_pattern = re.compile(stats_pattern)
        if not os.path.exists(self.stats_dir):
            raise OSError('Stats directory does not exist: %s'
                          % self.stats_dir)
        files = [f for f in os.listdir(self.stats_dir)
                 if re.search(stats_pattern, f)]
        files = natsorted(files)
        if not files:
            raise OSError('No illumination statistic files found in "%s"'
                          % self.stats_dir)
        self._illumstats_files = files
        return self._illumstats_files

    @property
    def illumstats_metadata(self):
        '''
        Returns
        -------
        List[IllumstatsImageMetadata]
            metadata for each illumination statistic file in `stats_dir`

        Note
        ----
        Metadata information is retrieved from the filenames using regular
        expressions.

        Raises
        ------
        RegexpError
            when required information could not be retrieved from filename
        '''
        self._illumstats_metadata = list()
        for f in self.illumstats_files:
            md = IllumstatsImageMetadata()
            regexp = utils.regex_from_format_string(self.cfg.STATS_FILE)
            match = re.search(regexp, f)
            if match:
                md.channel_name = match.group('channel')
                md.cycle_name = match.group('cycle')
                md.filename = f
            else:
                raise RegexpError('Can\'t determine channel and cycle number '
                                  'from illumination statistic file "%s" '
                                  'using provided format "%s".\n'
                                  'Check your configuration settings!'
                                  % (f, self.cfg['STATS_FILE']))
            self._illumstats_metadata.append(md)
        return self._illumstats_metadata

    @property
    def illumstats_images(self):
        '''
        Returns
        -------
        IllumstatsImages
            illumination statistics images object for each image file in
            `stats_dir`

        Note
        ----
        Image objects have lazy loading functionality, i.e. the actual image
        pixel array is only loaded into memory once the corresponding attribute
        (property) is accessed.
        '''
        self._illumstats_images = list()
        for i, f in enumerate(self.illumstats_files):
            img = IllumstatsImages.create_from_file(
                    filename=os.path.join(self.stats_dir, f),
                    metadata=self.illumstats_metadata[i],
                    library=self.library)
            self._illumstats_images.append(img)
        return self._illumstats_images

    @property
    def registration_metadata(self):
        return self._registration_metadata

    @cached_property
    def channels(self):
        '''
        Returns
        -------
        Set[str]
            names of channels in the cycle

        Note
        ----
        Each image in the cycle must have the same number of channels.
        '''
        self._channels = set([md.channel_name for md in self.image_metadata])
        return self._channels
