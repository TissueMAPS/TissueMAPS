import re
import os
from natsort import natsorted
from cached_property import cached_property
from . import utils
from .image import is_image_file
from .image import ChannelImage
from .metadata import ChannelImageMetadata
from .metadata import MosaicMetadata
# from .metadata import SegmentationImageMetadata
from .metadata import IllumstatsImageMetadata
from .shift import ShiftDescription
from .errors import RegexpError


class Cycle(object):
    '''
    Base class for the representation of a *cycle*.

    A *cycle* represents an individual image acquisition time point
    as part of a time series experiment and corresponds to a folder on disk.

    The `Cycle` class provides attributes and methods for accessing the
    contents of this folder. It provides for example the names of subfolders
    and files based on configuration settings.

    The contents of a *cycle* folder belong to a *plate*, i.e. the utensil
    holding the imaged sample(s). A plate can either be a *well plate*
    with multiple samples or a *slide* with only a single sample.

    See also
    --------
    `experiment.Experiment`_
    `plates.WellPlate`_
    `plates.Slide`_
    '''

    def __init__(self, cycle_dir, cfg, user_cfg, library='vips'):
        '''
        Initialize an instance of class Cycle.

        Parameters
        ----------
        cycle_dir: str
            absolute path to the cycle directory
        cfg: Dict[str, str]
            configuration settings
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
        A cycle represents a time point in a time series. The cycle identifier
        is the one-based index of the cycle in this sequence.
        The id is encoded in the subexperiment folder name by an integer.
        The format of the folder name is defined by
        the key *CYCLE_DIR* in the configuration settings file.
        It is used to build a named regular expressions for the extraction of
        the *cycle_num* from the folder name.

        Returns
        -------
        int
            cycle identifier number

        Raises
        ------
        RegexpError
            when cycle identifier number cannot not be determined from format
            string
        '''
        regexp = utils.regex_from_format_string(self.cfg['CYCLE_DIR'])
        m = re.search(regexp, self.name)
        if not m:
            raise RegexpError('Can\'t determine cycle id number from '
                              'subexperiment folder "%s" '
                              'using provided format "%s".\n'
                              'Check your configuration settings!'
                              % (self.name, self.cfg['CYCLE_DIR']))
        self._id = int(m.group('cycle_id'))
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
    def image_upload_dir(self):
        '''
        Returns
        -------
        str
            absolute path to directory that contains the uploaded images

        Note
        ----
        Creates the directory if it doesn't exist.
        '''
        self._image_upload_dir = self.cfg['IMAGE_UPLOAD_DIR'].format(
                                                cycle_dir=self.dir,
                                                sep=os.path.sep)
        if not os.path.exists(self._image_upload_dir):
            os.mkdir(self._image_upload_dir)
        return self._image_upload_dir

    @cached_property
    def additional_upload_dir(self):
        '''
        Returns
        -------
        str
            absolute path to directory that contains the uploaded
            additional, microscope-specific metadata files

        Note
        ----
        Creates the directory if it doesn't exist.
        '''
        self._additional_upload_dir = self.cfg['ADDITIONAL_UPLOAD_DIR'].format(
                                                cycle_dir=self.dir,
                                                sep=os.path.sep)
        if not os.path.exists(self._additional_upload_dir):
            os.mkdir(self._additional_upload_dir)
        return self._additional_upload_dir

    @cached_property
    def ome_xml_dir(self):
        '''
        Returns
        -------
        str
            absolute path to directory that contains the extracted OMEXML files

        Note
        ----
        Creates the directory if it doesn't exist.
        '''
        self._ome_xml_dir = self.cfg['OME_XML_DIR'].format(
                                                cycle_dir=self.dir,
                                                sep=os.path.sep)
        if not os.path.exists(self._ome_xml_dir):
            os.mkdir(self._ome_xml_dir)
        return self._ome_xml_dir

    @cached_property
    def ome_xml_files(self):
        '''
        Returns
        -------
        List[str]
            names of XML files in `ome_xml_dir`

        Raises
        ------
        OSError
            when `ome_xml_dir` does not exist or when no XML files are found
            in `ome_xml_dir`
        '''
        if not os.path.exists(self.ome_xml_dir):
            raise OSError('OMEXML directory does not exist: %s'
                          % self.image_dir)
        files = [f for f in os.listdir(self.ome_xml_dir)
                 if f.endswith('.ome.xml')]
        files = natsorted(files)
        if not files:
            raise OSError('No XML files found in "%s"' % self.ome_xml_dir)
        self._ome_xml_files = files
        return self._ome_xml_files

    @cached_property
    def metadata_dir(self):
        '''
        Returns
        -------
        str
            absolute path to directory that contains the metadata file

        Note
        ----
        Creates the directory if it doesn't exist.
        '''
        self._image_metadata_dir = self.cfg['METADATA_DIR'].format(
                                                cycle_dir=self.dir,
                                                sep=os.path.sep)
        if not os.path.exists(self._image_metadata_dir):
            os.mkdir(self._image_metadata_dir)
        return self._image_metadata_dir

    @cached_property
    def image_dir(self):
        '''
        Returns
        -------
        str
            path to the folder holding the image files

        Note
        ----
        Creates the directory if it doesn't exist.
        '''
        self._image_dir = self.cfg['IMAGE_DIR'].format(
                                                cycle_dir=self.dir,
                                                sep=os.path.sep)
        if not os.path.exists(self._image_dir):
            os.mkdir(self._image_dir)
        return self._image_dir

    @cached_property
    def image_files(self, reader=None):
        '''
        Returns
        -------
        List[str]
            names of image files in `image_dir`

        Raises
        ------
        OSError
            when `image_dir` does not exist or when no image files are found
            in `image_dir`

        See also
        --------
        `image.is_image_file`_
        '''
        if not os.path.exists(self.image_dir):
            raise OSError('Image directory does not exist: %s'
                          % self.image_dir)
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
            name of YAML file containing the metadata for each image file
        '''
        self._image_metadata_file = self.cfg['IMAGE_METADATA_FILE']
        return self._image_metadata_file

    @cached_property
    def image_metadata(self):
        '''
        Returns
        -------
        List[ChannelImageMetadata]
            metadata for each image file in `image_dir` (the `.metadata` YAML
            file maps each image file to its corresponding metadata)

        Raises
        ------
        OSError
            when metadata file does not exist

        See also
        --------
        `metadata.ChannelImageMetadata`_
        '''
        filename = os.path.join(self.metadata_dir,
                                self.image_metadata_file)
        if not os.path.exists(filename):
            raise OSError('Metadata file "%s" does not exists.' % filename)
        metadata = utils.read_json(filename)
        self._image_metadata = list()
        for f in natsorted(metadata.keys()):
            self._image_metadata.append(ChannelImageMetadata(metadata[f]))
        return self._image_metadata

    @cached_property
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
        for i, f in enumerate(self.image_files):
            img = ChannelImage.create_from_file(
                    os.path.join(self.image_dir, f), self.image_metadata[i],
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
        self._stats_dir = self.cfg['STATS_DIR'].format(
                                            cycle_dir=self.dir,
                                            sep=os.path.sep)
        if not os.path.exists(self._stats_dir):
            os.mkdir(self._stats_dir)
        return self._stats_dir

    @cached_property
    def stats_files(self):
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
        stats_pattern = self.cfg['STATS_FILE'].format(
                                            cycle=self.name,
                                            channel='\w+')
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
        self._stats_files = files
        return self._stats_files

    @property
    def stats_metadata(self):
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
        self._stats_metadata = list()
        for f in self.stats_files:
            md = IllumstatsImageMetadata()
            regexp = utils.regex_from_format_string(self.cfg['STATS_FILE'])
            m = re.search(regexp, f)
            if m:
                md.channel = m.group('channel')
                md.cycle = m.group('cycle')
                md.filename = f
            else:
                raise RegexpError('Can\'t determine channel and cycle number '
                                  'from illumination statistic file "%s" '
                                  'using provided format "%s".\n'
                                  'Check your configuration settings!'
                                  % (f, self.cfg['STATS_FILE']))
            self._stats_metadata.append(md)
        return self._stats_metadata

    @cached_property
    def shift_dir(self):
        '''
        Returns
        -------
        str
            path to directory holding shift descriptor file

        Note
        ----
        Creates the directory if it doesn't exist.
        '''
        self._shift_dir = self.cfg['SHIFT_DIR'].format(
                                                cycle_dir=self.dir,
                                                sep=os.path.sep)
        if not os.path.exists(self._shift_dir):
            os.mkdir(self._shift_dir)
        return self._shift_dir

    @cached_property
    def shift_file(self):
        '''
        Returns
        -------
        str
            name of shift descriptor file in `shift_dir`

        Raises
        ------
        OSError
            when `shift_dir` does not exist or when no
            shift descriptor file is found
        '''
        shift_pattern = self.cfg['SHIFT_FILE'].format(cycle=self.name)
        if not os.path.exists(self.shift_dir):
            raise OSError('Shift directory does not exist: %s'
                          % self.shift_dir)
        files = [f for f in os.listdir(self.shift_dir)
                 if re.search(shift_pattern, f)]
        if len(files) == 0:
            raise OSError(
                'No shift descriptor file found in "%s"' % self.shift_dir)
        self._shift_file = natsorted(files)[-1]
        return self._shift_file

    @property
    def shift_descriptions(self):
        '''
        Returns
        -------
        List[ShiftDescription]
            shift description for each image file in `image_dir`

        See also
        --------
        `shift.ShiftDescription`_
        '''
        filename = os.path.join(self.shift_dir, self.shift_file)
        content = utils.read_json(filename)
        self._shift_descriptions = list()
        # by matching the sites and wells, we ensure that the correct shift
        # description is assigned to each image
        sites = [e['site'] for e in content]
        for m in self.image_metadata:
            ix = sites.index(m.site)
            self._shift_descriptions.append(ShiftDescription(content[ix]))
        return self._shift_descriptions

    @property
    def layer_names(self):
        '''
        Returns
        -------
        Dict[Tuple[str], str]
            unique name for each layer of this cycle, i.e. the set of images
            of the same *channel*

        Note
        ----
        If the attribute is not set, it will be attempted to retrieve the
        information from the user configuration. If the information is
        not available, default names are created, which are a unique
        combination of *cycle* and *channel* names.
        '''
        if 'LAYER_NAMES' in self.user_cfg.keys():
            self._layer_names = self.user_cfg['LAYER_NAMES']
        else:
            self._layer_names = {
                img.metadata.channel:
                    self.cfg['LAYER_NAME'].format(
                        cycle=img.metadata.cycle,
                        channel=img.metadata.channel)
                for img in self.images
            }
        return self._layer_names

    @property
    def layer_metadata(self):
        '''
        Returns
        -------
        List[MosaicMetadata]
            metadata for each layer
        '''
        self._layer_metadata = list()
        channels = list(set([md.channel for md in self.image_metadata]))
        for c in channels:
            layer_name = self.layer_names[c]
            images = list()
            images.extend([img for img in self.images
                           if img.metadata.channel == c])
            self._layer_metadata.append(
                MosaicMetadata.create_from_images(images, layer_name))
        return self._layer_metadata

    # @property
    # def segmentation_dir(self):
    #     '''
    #     Segmentations are stored as image files in a single folder per
    #     experiment. The corresponding cycles is referred to as "reference"
    #     cycle, because its images are used as references for registration.
    #     The format of the folder name is defined by the key
    #     *SEGMENTATION_DIR* in the configuration settings file.

    #     Returns
    #     -------
    #     str
    #         absolute path to the folder containing the segmentation image files
    #     '''
    #     if self.reference:
    #         self._segmentation_dir = self.cfg['SEGMENTATION_DIR'].format(
    #                                         cycle_dir=self.dir,
    #                                         sep=os.path.sep)
    #     else:
    #         self._segmentation_dir = None
    #     return self._segmentation_dir

    # @cached_property
    # def segmentation_files(self):
    #     '''
    #     Returns
    #     -------
    #     List[str]
    #         names of segmentation files in `segmentation_dir`

    #     Raises
    #     ------
    #     OSError
    #         when cycle is the reference cycle, but `segmentation_dir` does not
    #         exist or when cycle is the reference cycle, but no image files are
    #         found in `segmentation_dir`

    #     See also
    #     --------
    #     `image.is_image_file`_
    #     '''
    #     if self.reference:
    #         if not os.path.exists(self.segmentation_dir):
    #             raise OSError('Segmentation directory does not exist: %s'
    #                           % self.segmentation_dir)
    #         files = [f for f in os.listdir(self.segmentation_dir)
    #                  if is_image_file(f)]
    #         files = natsorted(files)
    #         if not files:
    #             raise OSError('No supported image files found in "%s"'
    #                           % self.segmentation_dir)
    #         self._segmentation_files = files
    #     else:
    #         self._segmentation_files = list()

    #     return self._segmentation_files

    # @property
    # def segmentation_metadata_file(self):
    #     '''
    #     The `.metadata` YAML file contains a sequence of mappings
    #     (key-value pairs).

    #     Returns
    #     -------
    #     str
    #         name of YAML file containing the metadata for each segmentation
    #         file (returns ``None`` if cycle is not the reference cycle)
    #     '''
    #     if self.reference:
    #         self._segmentation_metadata_file = \
    #                                 self.cfg['SEGMENTATION_METADATA_FILE']
    #     else:
    #         self._segmentation_metadata_file = None
    #     return self._segmentation_metadata_file

    # @cached_property
    # def segmentation_metadata(self):
    #     '''
    #     Returns
    #     -------
    #     List[SegmentationImageMetadata]
    #         metadata for each segmentation image file in `segmentation_dir`

    #     See also
    #     --------
    #     `metadata.SegmentationImageMetadata`_
    #     '''
    #     filename = os.path.join(self.metadata_dir,
    #                             self.segmentation_metadata_file)
    #     if self.reference:
    #         content = utils.read_json(filename)
    #         metadata = list()
    #         for f in self.segmentation_files:
    #             metadata.append(SegmentationImageMetadata(content[f]))
    #         self._segmentation_metadata = metadata
    #     else:
    #         self._segmentation_metadata = list()
    #     return self._segmentation_metadata

    # @property
    # def segmentation_shifts(self):
    #     '''
    #     Returns
    #     -------
    #     List[ShiftDescription]
    #         shift description for each image file in `segmentation_dir`

    #     See also
    #     --------
    #     `shift.ShiftDescription`_
    #     '''
    #     filename = os.path.join(self.shift_dir, self.shift_file)
    #     content = utils.read_yaml(filename)
    #     self._shift_descriptions = list()
    #     # by matching the sites, we ensure that the correct shift description
    #     # is assigned to each image
    #     sites = [e.site for e in content]
    #     for m in self.segmentation_metadata:
    #         ix = sites.index(m.site)
    #         self._shift_descriptions.append(ShiftDescription(content[ix]))
    #     return self._shift_descriptions

    # @property
    # def object_types(self):
    #     '''
    #     Returns
    #     -------
    #     Set[str]
    #         unique objects names, e.g. ``{"Cells", "Nuclei"}``
    #     '''
    #     if self.segmentation_files:
    #         self._object_types = set([m.objects
    #                                   for m in self.segmentation_metadata])
    #     else:
    #         self._object_types = set()
    #     return self._object_types

    def __str__(self):
        return('experiment "%s" - cycle #%s: "%s"'
               % (self.experiment, self.name, self.id))

    def __unicode__(self):
        return self.__str__()
