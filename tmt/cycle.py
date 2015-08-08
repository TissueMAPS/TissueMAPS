import re
import os
from natsort import natsorted
from utils import regex_from_format_string
from image import is_image_file
from metadata import ChannelMetadata
from metadata import SegmentationMetadata
from illumstats import Illumstats
from shift import ShiftDescription
from reader import read_yaml


class Cycle(object):
    '''
    Base class for a cycle, i.e. an individual image acquisition time point
    as part of a time series experiment.

    A cycle corresponds to a plate, i.e. the utensil holding the imaged
    sample(s). This can either be a multi-well plate with a different
    sample in each well (well plate) or a single-well plate (slide) holding
    only one sample.

    See also
    --------
    `experiment.Experiment`_
    `plates.WellPlate`_
    `plates.Slide`_
    '''

    def __init__(self, cycle_dir, cfg, reference=False):
        '''
        Initialize an instance of class Cycle.

        Parameters
        ----------
        cycle_dir: str
            absolute path to the cycle directory
        cfg: Dict[str, str]
            configuration settings
        reference: bool, optional
            whether the cycle is the reference cycle
        '''
        self.cycle_dir = os.path.abspath(cycle_dir)
        self.cfg = cfg
        self._image_files = None
        self._images = None
        self._image_metadata = None
        self._stats_files = None
        self._shift_file = None

    @property
    def name(self):
        '''
        Returns
        -------
        str
            name of the subexperiment folder on disk
        '''
        self._name = os.path.basename(self.cycle_dir)
        return self._name

    @property
    def experiment(self):
        '''
        Returns
        -------
        str
            name of the corresponding parent experiment folder
        '''
        self._experiment = os.path.basename(os.path.dirname(self.cycle_dir))
        return self._experiment

    @property
    def id(self):
        '''
        A cycle represents a time point in a time series. The cycle identifier
        is the one-based index of the cycle in this sequence.

        The id is encoded in the subexperiment folder name corresponding to
        the cycle with an integer. The format of the folder name is defined by
        the key *CYCLE_FOLDER_FORMAT* in the configuration settings file.
        It is used to build a named regular expressions for the extraction of
        the *cycle_num* from the folder name.

        Returns
        -------
        int
            cycle identifier number

        Raises
        ------
        ValueError
            when cycle number cannot not be determined from format string
        '''
        regexp = regex_from_format_string(self.cfg['CYCLE_FOLDER_FORMAT'])
        m = re.search(regexp, self.name)
        if not m:
            raise ValueError('Can\'t determine cycle id number from '
                             'subexperiment folder "%s" '
                             'using provided format "%s".\n'
                             'Check your configuration settings!'
                             % (self.name,
                                self.cfg['CYCLE_FOLDER_FORMAT']))
        self._cycle_id = int(m.group('cycle_num'))
        return self._id

    @property
    def image_dir(self):
        '''
        Returns
        -------
        str
            path to the folder holding the image files
        '''
        if self._image_dir is None:
            folder = self.cfg['IMAGE_FOLDER_FORMAT'].format(
                            experiment_dir=self.experiment_dir,
                            subexperiment=self.subexperiment,
                            sep=os.path.sep)
            self._image_dir = folder
        return self._image_dir

    @property
    def image_files(self, reader=None):
        '''
        Returns
        -------
        List[str]
            absolute path to each image file in `image_dir`

        Raises
        ------
        OSError
            when `image_dir` does not exist
        IOError
            when no image files are found in `image_dir`

        See also
        --------
        `image.is_image_file`_
        '''
        if self._image_files is None:
            if not os.path.exists(self.image_dir):
                raise OSError('Image directory does not exist: %s'
                              % self.image_dir)
            files = [os.path.join(self.image_dir, f)
                     for f in os.listdir(self.image_dir) if is_image_file(f)]
            files = natsorted(files)
            if not files:
                raise IOError('No supported image files found in "%s"'
                              % self.image_dir)
            self._image_files = files
        return self._image_files

    @property
    def n_images(self):
        '''
        Returns
        -------
        int
            total number of images for this cycle
        '''
        self._n_images = len(self.image_files)
        return self._n_images

    @property
    def image_metadata_file(self):
        '''
        Returns
        -------
        str
            absolute path to the YAML file containing the metadata for each
            image file
        '''
        self._image_metadata_file = os.path.join(
                                        self.image_dir,
                                        self.cfg['IMAGE_METADATA_FILE_NAME'])
        return self._image_metadata_file

    @property
    def image_metadata(self):
        '''
        The `.metadata` YAML file contains a sequence of mappings
        (key-value pairs)::

            - filename: str
              site: int
              row: int
              column: int
              channel: str
              ...
            ...

        Returns
        -------
        List[ChannelMetadata]
            metadata for each image file in `image_dir`

        Raises
        ------
        OSError
            when `image_metadata_file` does not exist

        See also
        --------
        `metadata.ChannelMetadata`_
        '''
        if self._image_metadata is None:
            if not os.path.exists(self._image_metadata_file):
                raise OSError('Metadata file "%s" does not exists.'
                              % self._image_metadata_file)
            file_content = read_yaml(self._image_metadata_file)
            # by matching the filenames, we make sure that the correct
            # metadata is assigned to each image
            filenames = [c['filename'] for c in file_content]
            self._image_metadata = list()
            for f in self.image_files:
                ix = filenames.index(f)
                self._image_metadata.append(ChannelMetadata(file_content[ix],
                                                            cycle=self.id))
        return self._image_metadata

    @property
    def channels(self):
        '''
        Returns
        -------
        Set[str]
            unique channel names
        '''
        self._channels = set([m['channel'] for m in self.image_metadata])
        return self._channels

    @property
    def n_channels(self):
        '''
        Returns
        -------
        int
            total number of channels for this cycle
        '''
        self._n_cycles = len(self.channels)
        return self._n_cycles

    @property
    def n_sites(self):
        '''
        Returns
        -------
        int
            total number of image acquisition sites for this cycle
        '''
        self._n_sites = len(set([m['site'] for m in self.image_metadata]))
        return self._n_sites

    @property
    def stats_dir(self):
        '''
        Returns
        -------
        str
            path to the directory holding illumination statistic files
        '''
        self._stats_dir = self.cfg['STATS_FOLDER_FORMAT'].format(
                            experiment_dir=self.experiment_dir,
                            subexperiment=self.subexperiment,
                            sep=os.path.sep)
        return self._stats_dir

    @property
    def stats_files(self):
        '''
        Returns
        -------
        List[str]
            absolute path to each illumination correction file in `stats_dir`

        Raises
        ------
        OSError
            when `stats_dir` does not exist
        IOError
            when no illumination statistic files are found in `stats_dir`
        '''
        if self._stats_files is None:
            stats_pattern = self.cfg['STATS_FILE_FORMAT'].format(channel='\d+')
            stats_pattern = re.compile(stats_pattern)
            if not os.path.exists(self.stats_dir):
                raise OSError('Stats directory does not exist: %s'
                              % self.stats_dir)
            files = [os.path.join(self.stats_dir, f)
                     for f in os.listdir(self.stats_dir)
                     if re.search(stats_pattern, f)]
            files = natsorted(files)
            if not files:
                raise IOError('No illumination statistic files found in "%s"'
                              % self.stats_dir)
            self._stats_files = files
        return self._stats_files

    @property
    def illumination_statistics(self):
        '''
        Returns
        -------
        List[Illumstats]
            pre-calculated illumination statistics for each channel

        See also
        --------
        `illumstats.Illumstats`_
        '''
        self._illumination_statistics = [Illumstats(f, self.cfg)
                                         for f in self.stats_files]
        return self._illumination_statistics

    @property
    def shift_dir(self):
        '''
        Returns
        -------
        str
            path to directory holding shift descriptor file
        '''
        self._shift_dir = self.cfg['SHIFT_FOLDER_FORMAT'].format(
                            experiment_dir=self.experiment_dir,
                            subexperiment=self.subexperiment,
                            sep=os.path.sep)
        return self._shift_dir

    @property
    def shift_file(self):
        '''
        Returns
        -------
        str
            absolute path to the shift descriptor file in `shift_dir`

        Raises
        ------
        OSError
            when `shift_dir` does not exist
        IOError
            when no shift descriptor file is found in `shift_dir`
        '''
        if self._shift_file is None:
            shift_pattern = self.cfg['SHIFT_FILE_FORMAT']
            shift_pattern = re.compile(shift_pattern)
            if not os.path.exists(self.shift_dir):
                raise OSError('Shift directory does not exist: %s'
                              % self.shift_dir)
            files = [os.path.join(self.shift_dir, f)
                     for f in os.listdir(self.shift_dir)
                     if re.search(shift_pattern, f)]
            # there should only be one file, but in case there are more take
            # the first one
            files = natsorted(files)
            if not files:
                raise IOError('No shift descriptor file found in "%s" '
                              'that matches the provided pattern "%s".\n'
                              'Check your configuration settings!'
                              % (self.shift_dir,
                                 self.cfg['SHIFT_FILE_FORMAT']))
            if len(files) > 1:
                print('More than one shift descriptor files found in "%s".\n'
                      'Using file "%s".' % (self.shift_dir, files[0]))
            self._shift_file = files[0]
        return self._shift_file

    @property
    def image_shifts(self):
        '''
        Returns
        -------
        List[ShiftDescription]
            shift description for each image file in `image_dir`

        See also
        --------
        `shift.ShiftDescriptor`_
        '''
        file_content = read_yaml(self.shift_file)
        self._shift_description = list()
        # by matching the sites, we ensure that the correct shift description
        # is assigned to each image
        sites = [e.site for e in file_content]
        for m in self.image_metadata:
            ix = sites.index(m.site)
            self._shift_description.append(ShiftDescription(file_content[ix]))
        return self._shift_description

    @property
    def segmentation_dir(self):
        '''
        Segmentations are stored as image files in a single folder per
        experiment. The corresponding cycles is referred to as "reference"
        cycle, because its images are used as references for registration.
        The format of the folder name is defined by the key
        *SEGMENTATION_FOLDER_FORMAT* in the configuration settings file.

        Returns
        -------
        str
            absolute path to the folder containing the segmentation image files
        '''
        if self.reference:
            self._segmentation_dir = self.cfg['SEGMENTATION_FOLDER_FORMAT'].format(
                                            experiment_dir=self.experiment_dir,
                                            subexperiment=self.cycle_dir,
                                            sep=os.path.sep)
        else:
            self._segmentation_dir = ''
        return self._segmentation_dir

    @property
    def segmentation_files(self):
        '''
        Returns
        -------
        List[str]
            absolute path to each segmentation file in `segmentation_dir`

        Raises
        ------
        OSError
            when cycle is the reference cycle,
            but `segmentation_dir` does not exist
        IOError
            when cycle is the reference cycle,
            but no image files are found in `segmentation_dir`

        See also
        --------
        `image.is_image_file`_
        '''
        if self._segmentation_files is None:
            if self.reference:
                if not os.path.exists(self.image_dir):
                    raise OSError('Segmentation directory does not exist: %s'
                                  % self.segmentation_dir)
                files = [os.path.join(self.segmentation_dir, f)
                         for f in os.listdir(self.segmentation_dir)
                         if is_image_file(f)]
                files = natsorted(files)
                if not files:
                    raise IOError('No supported image files found in "%s"'
                                  % self.segmentation_dir)
                self._segmentation_files = files
            else:
                self._segmentation_files = list()

        return self._segmentation_files

    @property
    def segmentation_metadata_file(self):
        '''
        The `.metadata` YAML file contains a sequence of mappings
        (key-value pairs)::

            - filename: str
              site: int
              row: int
              column: int
              objects: str
              ...
            ...

        Returns
        -------
        str
            absolute path to the YAML file containing the metadata for each
            segmentation file
            (returns ``None`` if cycle is not the reference cycle)
        '''
        if self.reference:
            self._segmentation_metadata_file = os.path.join(
                                self.segmentation_dir,
                                self.cfg['SEGMENTATION_METADATA_FILE_NAME'])
        else:
            self._segmentation_metadata_file = ''
        return self._segmentation_metadata_file

    @property
    def segmentation_metadata(self):
        '''
        Returns
        -------
        List[SegmentationMetadata]
            metadata for each image file in `segmentation_dir`

        See also
        --------
        `metadata.SegmentationMetadata`_
        '''
        if self._segmentation_metadata is None:
            if self.reference:
                file_content = read_yaml(self.segmentation_metadata_file)
                # by matching the filenames, we make sure that the correct
                # metadata is assigned to each segmentation image
                filenames = [c['filename'] for c in file_content]
                metadata = list()
                for f in self.image_files:
                    ix = filenames.index(f)
                    metadata.append(SegmentationMetadata(file_content[ix],
                                                         cycle=self.id))
                self._segmentation_metadata = metadata
            else:
                self._segmentation_metadata = list()
        return self._segmentation_metadata

    @property
    def segmentation_shifts(self):
        '''
        Returns
        -------
        List[ShiftDescription]
            shift description for each image file in `segmentation_dir`

        See also
        --------
        `shift.ShiftDescriptor`_
        '''
        file_content = read_yaml(self.shift_file)
        self._shift_description = list()
        # by matching the sites, we ensure that the correct shift description
        # is assigned to each image
        sites = [e.site for e in file_content]
        for m in self.segmentation_metadata:
            ix = sites.index(m.site)
            self._shift_description.append(ShiftDescription(file_content[ix]))
        return self._shift_description

    @property
    def objects(self):
        '''
        Returns
        -------
        Set[str]
            unique object names
        '''
        if self.segmentation_files:
            self._objects = set([m['objects']
                                for m in self.segmentation_metadata])
        else:
            self._objects = set()
        return self._objects

    @property
    def n_objects(self):
        '''
        Returns
        -------
        int
            total number of unique object names
        '''
        self._n_objects = len(self.objects)
        return self._n_objects

    def __str__(self):
        return 'experiment "%s" - cycle #%s' % (self.experiment, self.cycle)

    def __unicode__(self):
        return self.__str__()
