import re
import os
import logging
from lxml import etree
from natsort import natsorted
from cached_property import cached_property
from . import config
from . import utils
from .upload import Upload
from .cycle import Cycle
from .metadata import MosaicMetadata
from .config_setters import UserConfiguration
from .config_setters import TmlibConfiguration
from .errors import NotSupportedError
from .readers import UserConfigurationReader

logger = logging.getLogger(__name__)


class ExperimentFactory(object):

    '''
    Factory class to create an experiment object.

    The type of the returned object depends on the user configuration
    and the experimental setup.
    '''

    def __init__(self, experiment_dir, library='vips'):
        '''
        Initialize an instance of class ExperimentFactory.

        Parameters
        ----------
        experiment_dir: str
            absolute path to experiment folder
        library: str, optional
            image library that should be used
            (options: ``"vips"`` or ``"numpy"``, default: ``"vips"``)
        '''
        self.experiment_dir = os.path.expandvars(experiment_dir)
        self.experiment_dir = os.path.expanduser(self.experiment_dir)
        self.experiment_dir = os.path.abspath(self.experiment_dir)
        self.library = library

    @property
    def user_cfg_file(self):
        '''
        Returns
        -------
        str
            absolute path to experiment-specific user configuration file
        '''
        return self.cfg.USER_CFG_FILE.format(
                    experiment_dir=self.experiment_dir, sep=os.path.sep)

    @property
    def cfg(self):
        '''
        Returns
        -------
        TmlibConfiguration
            file system configuration settings

        See also
        --------
        `tmlib.cfg_setters.TmlibConfiguration`_
        '''
        return TmlibConfiguration(config)

    @cached_property
    def user_cfg(self):
        '''
        Returns
        -------
        UserConfiguration
            experiment-specific configuration settings provided by the user
            in YAML format

        See also
        --------
        `tmlib.cfg_setters.UserConfiguration`_
        '''
        # TODO: shall we do this via the database instead?
        logger.debug('loading user configuration file: %s', self.user_cfg_file)
        with UserConfigurationReader() as reader:
            config_settings = reader.read(self.user_cfg_file)
        return UserConfiguration(config_settings)

    def create(self):
        '''
        Create an instance of an instance of a subclass of the `Experiment`
        base class. The type depends on the experiment-specific user
        configuration settings.

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

        Returns
        -------
        Slide or WellPlate
        '''
        logger.debug('using the "%s" image library', self.library)
        if self.user_cfg.WELLPLATE_FORMAT:
            return WellPlate(
                    self.experiment_dir, self.cfg, self.user_cfg, self.library)
        else:
            return Slide(
                    self.experiment_dir, self.cfg, self.user_cfg, self.library)


class Experiment(object):
    '''
    Base class for experiments.

    An *experiment* represents a folder on disk that contains a set of image
    files and additional data associated with the images, such as metadata
    or measurement data, for example.
    The structure of the directory tree and the names of files are defined
    via Python format strings in the configuration settings file.

    An *experiment* consists of one or more *cycles*. A *cycle* represents a
    particular time point of image acquisition for a given sample and
    corresponds to a subfolder in the *experiment* directory.
    In the simplest case, the experiments consists only of a single round of
    image acquisition. However, it may also consist of a time series,
    i.e. several iterative rounds of image acquisitions, where the same
    the sample is repeatedly imaged at the same positions.

    The names of the *cycle* folders encode the name of the experiment
    as well as the *cycle* identifier number, i.e. the one-based index of
    the time series sequence.

    See also
    --------
    `tmlib.cycle.Cycle`_
    `tmlib.cfg`_
    '''

    def __init__(self, experiment_dir, cfg, user_cfg, library):
        '''
        Initialize an instance of class Experiment.

        Parameters
        ----------
        experiment_dir: str
            absolute path to experiment folder
        cfg: TmlibConfigurations
            configuration settings for names of directories and files on disk
        library: str
            image library that should be used
            (options: ``"vips"`` or ``"numpy"``)

        See also
        --------
        `tmlib.cfg_setters.TmlibConfiguration`_
        `tmlib.cfg`_
        '''
        self.experiment_dir = experiment_dir
        self.cfg = cfg
        self.user_cfg = user_cfg
        self.library = library

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
        # format_string = self.cfg.CYCLE_DIR.format(
        #     experiment_name=self.name, cycle_id='{cycle_id}')
        format_string = self.cfg.CYCLE_SUBDIR
        regexp = utils.regex_from_format_string(format_string)
        return True if re.match(regexp, folder) else False

    @cached_property
    def cycles_dir(self):
        '''
        Returns
        -------
        str
            absolute path to the folder, where `cycles` are located
            (`cycles` are represented by subfolders of `cycle_dir`)

        Note
        ----
        The directory is created if it doesn't exist.
        '''
        self._cycles_dir = self.cfg.CYCLE_DIR.format(
                                        experiment_dir=self.dir,
                                        sep=os.path.sep)
        if not os.path.exists(self._cycles_dir):
            logger.debug('create directory for cycles: %s', self._cycles_dir)
            os.mkdir(self._cycles_dir)
        return self._cycles_dir

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
            os.path.join(self.cycles_dir, d)
            for d in os.listdir(self.cycles_dir)
            if os.path.isdir(os.path.join(self.cycles_dir, d))
            and self._is_cycle_dir(d)
        ]
        cycle_dirs = natsorted(cycle_dirs)
        self._cycles = [
                Cycle(d, self.cfg, self.user_cfg, self.library)
                for d in cycle_dirs
            ]
        return self._cycles

    @property
    def uploads_dir(self):
        '''
        Returns
        -------
        str
            absolute path to the directory, where uploaded files are located
            (each *upload* is stored in a separate subfolder of `uploads_dir`)

        Raises
        ------
        OSError
            when `uploads_dir` does not exist
        '''
        self._uploads_dir = self.cfg.UPLOAD_DIR.format(
                                            experiment_dir=self.dir,
                                            sep=os.path.sep)
        if not os.path.exists(self._uploads_dir):
            raise OSError('Uploads directory does not exist')
        return self._uploads_dir

    def _is_upload_subdir(self, folder):
        format_string = self.cfg.UPLOAD_SUBDIR
        regexp = utils.regex_from_format_string(format_string)
        return True if re.match(regexp, folder) else False

    @property
    def image_mapper_file(self):
        '''
        Returns
        -------
        str
            absolute path to the file that contains the mapping of original,
            uploaded image files and final image files that are stored
            per `cycles` upon extraction
        '''
        return os.path.join(self.uploads_dir, 'image_file_mapper.json')

    @property
    def uploads(self):
        '''
        The user can upload image files and optionally additional metadata
        files. If the experiment consists of multiple cycles, files for
        each cycle can be uploaded into a separate folder. These folders
        are sub-directories of the `upload_dir`.

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
            os.path.join(self.uploads_dir, d)
            for d in os.listdir(self.uploads_dir)
            if os.path.isdir(os.path.join(self.uploads_dir, d))
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
        If the attribute is not set, an attempt will be made to retrieve the
        information from the user configuration file. If the information is
        not available via the file, the last cycle is by default assigned as
        reference.
        '''
        if 'REFERENCE_CYCLE' in self.user_cfg.keys():
            self._reference_cycle = self.user_cfg.REFERENCE_CYCLE
            logger.debug('set reference cycle according to user configuration')
        else:
            cycle_names = natsorted([cycle.name for cycle in self.cycles])
            self._reference_cycle = cycle_names[-1]
            logger.debug('take last cycle as reference cycle')
        return self._reference_cycle

    def append_cycle(self):
        '''
        Create a new cycle object and add it to the end of the list of
        existing cycles.

        Returns
        -------
        WellPlate or Slide
            configured cycle object
        '''
        new_cycle_name = os.path.join(self.cycles_dir,
                                      self.cfg.CYCLE_SUBDIR.format(
                                            cycle_id=len(self.cycles)))
        new_cycle_dir = os.path.join(self.dir, new_cycle_name)
        logger.debug('add cycle: %s', os.path.basename(new_cycle_dir))
        logger.debug('create directory for new cycle: %s', new_cycle_dir)
        os.mkdir(new_cycle_dir)
        new_cycle = Cycle(new_cycle_dir, self.cfg, self.user_cfg, self.library)
        self.cycles.append(new_cycle)
        return new_cycle

    @cached_property
    def layers_dir(self):
        '''
        Returns
        -------
        str
            absolute path to the folder holding the layers (image pyramids)

        See also
        --------
        `tmlib.illuminati`_
        '''
        self._layers_dir = self.cfg.LAYERS_DIR.format(
                                            experiment_dir=self.experiment_dir,
                                            sep=os.path.sep)
        if not os.path.exists(self._layers_dir):
            logger.debug('create directory for layers pyramid directories: %s'
                         % self._layers_dir)
            os.mkdir(self._layers_dir)
        return self._layers_dir

    @cached_property
    def layer_names(self):
        '''
        Returns
        -------
        Dict[Tuple[str], str]
            unique name for each layer of this cycle, i.e. the set of images
            with the same *channel_id*, *plane_id* and *time_id*

        Note
        ----
        If the attribute is not set, it will be attempted to retrieve the
        information from the user configuration. If the information is
        not available, default names are created, which are a unique
        combination of *cycle* and *channel* names.
        '''
        if hasattr(self.user_cfg, 'LAYER_NAMES'):
            # self._layer_names = self.user_cfg.LAYER_NAMES
            raise NotSupportedError('TODO')
        else:
            self._layer_names = dict()
            for cycle in self.cycles:
                self._layer_names.update({
                    (md.channel_name, md.plane_id, md.time_id):
                        self.cfg.LAYER_NAME.format(
                            experiment_name=self.name,
                            channel_id=md.channel_name,
                            plane_id=md.plane_id,
                            time_id=md.time_id)
                    for md in cycle.image_metadata
                })
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
        channels = [cycle.channels for cycle in self.cycles]
        planes = self.focal_planes
        for c in channels:
            for p in planes:
                layer_name = self.layer_names[(c, p)]
                images = [
                    img for img in self.images
                    if img.metadata.channel_name == c
                    and img.metadata.plane_id == p
                ]
                self._layer_metadata.append(
                    MosaicMetadata.create_from_images(images, layer_name))
        return self._layer_metadata

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
        `tmlib.jterator`_
        '''
        self._data_filename = self.cfg.DATA_FILE.format(
                                            experiment_name=self.name,
                                            sep=os.path.sep)
        return self._data_filename

    @cached_property
    def acquisition_sites(self):
        '''
        Returns
        -------
        Set[int]
            identifier numbers of image acquisition sites in the experiment

        Note
        ----
        Each cycle in the experiment must have the same number of sites.
        '''
        self._acquisition_sites = set([
                md.site_id
                for cycle in self.cycles
                for md in cycle.image_metadata
        ])
        return self._acquisition_sites

    @cached_property
    def focal_planes(self):
        '''
        Returns
        -------
        Set[int]
            identifier numbers of focal planes of images in the experiment

        Note
        ----
        Each image in the experiment must have the same number of focal planes.
        '''
        self._focal_planes = set([
                md.plane_id
                for cycle in self.cycles
                for md in cycle.image_metadata
        ])
        return self._focal_planes

    def dump_metadata(self):
        experiment_e = etree.Element('experiment')
        experiment_e.set('name', self.name)

        cycles_e = etree.SubElement(experiment_e, 'cycles')

        for cycle in self.cycles:
            cycle_e = etree.SubElement(cycles_e, 'cycle')
            cycle_e.set('name', cycle.name)
            cycle_e.set('id', str(cycle.id))

            images_e = etree.SubElement(cycle_e, 'images')
            for i, md in enumerate(cycle.image_metadata):
                file_e = etree.SubElement(images_e, 'file')
                file_e.set('name', md.name)
                file_e.set('site_id', str(md.site_id))
                file_e.set('plane_id', str(md.plane_id))
                file_e.set('channel_id', str(md.channel_name))
                file_e.set('source_file_id', str(md.original_filename))

            acq_sites_e = etree.SubElement(cycle_e, 'acquisition_sites')
            acq_sites_e.set('upper_overhang', str(md.upper_overhang))
            acq_sites_e.set('lower_overhang', str(md.lower_overhang))
            acq_sites_e.set('left_overhang', str(md.left_overhang))
            acq_sites_e.set('right_overhang', str(md.right_overhang))
            sites = [md.site for md in cycle.image_metadata]
            for i, s in enumerate(self.acquisition_sites):
                ix = sites.index(s)
                md = cycle.image_metadata[ix]
                site_e = etree.SubElement(acq_sites_e, 'site')
                site_e.set('id', str(i+1))
                site_e.set('y_shift', str(md.y_shift))
                site_e.set('x_shift', str(md.x_shift))
                site_e.set('well_id', str(md.well_id))
                site_e.set('row_index', str(md.row_index))
                site_e.set('col_index', str(md.col_index))

            channels_e = etree.SubElement(cycle_e, 'channels')
            for i, c in enumerate(cycle.channels):
                channel_e = etree.SubElement(channels_e, 'channel')
                channel_e.set('id', str(i+1))
                channel_e.set('name', c)

            focal_planes_e = etree.SubElement(cycle_e, 'focal_planes')
            for i, p in enumerate(self.focal_planes):
                plane_e = etree.SubElement(focal_planes_e, 'plane')
                plane_e.set('id', str(i+1))

        uploads_e = etree.SubElement(experiment_e, 'uploads')
        # TODO

        print etree.tostring(experiment_e, pretty_print=True,
                             xml_declaration=True)

        doc = etree.ElementTree(experiment_e)
        with open(os.path.join(self.dir, self.metadata_file), 'w') as f:
            doc.write(f, pretty_print=True, xml_declaration=True)


class WellPlate(Experiment):

    '''
    A well plate represents a container with multiple reservoirs for different
    samples that might be stained independently, but imaged under the same
    conditions.

    There are different well plate *formats*, which encode the number of wells
    in the well, e.g. "384".
    '''

    SUPPORTED_PLATE_FORMATS = {96, 384}

    def __init__(self, experiment_dir, cfg, user_cfg, library):
        '''
        Initialize an instance of class WellPlate.

        Parameters
        ----------
        experiment_dir: str
            absolute path to experiment folder
        cfg: TmlibConfigurations
            configuration settings for names of directories and files on disk
        library: str
            image library that should be used
            (options: ``"vips"`` or ``"numpy"``)

        See also
        --------
        `tmlib.cfg_setters.TmlibConfiguration`_
        `tmlib.cfg`_
        '''
        super(WellPlate, self).__init__(experiment_dir, cfg, user_cfg, library)
        self.experiment_dir = experiment_dir
        self.cfg = cfg
        self.user_cfg = user_cfg
        self.library = library

    @property
    def plate_format(self):
        '''
        Returns
        -------
        plate_format: int
            number of wells in the plate (supported: 96 or 384)

        Note
        ----
        Information is obtained from user configurations.

        Raises
        ------
        ValueError
            when provided plate format is not supported
        '''
        self._plate_format = self.user_cfg.NUMBER_OF_WELLS
        if self._plate_format not in self.SUPPORTED_PLATE_FORMATS:
            raise ValueError(
                    'Well plate format must be either "%s"' % '" or "'.join(
                            [str(e) for e in self.SUPPORTED_PLATE_FORMATS]))
        return self._plate_format

    @property
    def dimensions(self):
        '''
        Returns
        -------
        Tuple[int]
            number of wells in the plate on the vertical and horizontal axis,
            i.e. number of rows and columns
        '''
        if self.plate_format == 96:
            self._dimensions = (8, 12)
        elif self.plate_format == 384:
            self._dimensions = (16, 24)
        return self._dimensions

    @property
    def well_coordinates(self):
        '''
        Returns
        -------
        List[Tuple[int]]
            zero-based row, column position of each well in the plate
        '''
        self._well_coordinates = [
            (self.map_well_id_to_position(w)[0]-1,
             self.map_well_id_to_position(w)[1]-1)
            for w in self.wells
        ]
        return self._well_coordinates

    @cached_property
    def wells(self):
        '''
        Returns
        -------
        Set[str]
            identifier string (capital letter for row position and
            one-based index number for column position) for each imaged
            well of the plate
        '''
        # TODO
        self._wells = set([md.well_id for md in self.image_metadata])
        return self._wells

    @property
    def n_wells(self):
        '''
        Returns
        -------
        int
            number of imaged wells in plate

        Note
        ----
        The total number of potentially available wells in the plate is given
        by the well plate `format`, e.g. 384 in case of a "384 well plate".
        '''
        self._n_wells = len(set(self.well_positions))
        return self._n_wells

    @staticmethod
    def map_well_id_to_position(well_id):
        '''
        Mapping of the identifier string representation to the
        one-based index position, e.g. "A02" -> (1, 2)

        Parameters
        ----------
        well_id: str
            identifier string representation of a well

        Returns
        -------
        Tuple[int]
            one-based row, column position of a given well within the plate

        Examples
        --------
        >>>WellPlate.map_well_id_to_position("A02")
        (1, 2)
        '''
        row_name, col_name = re.match(r'([A-Z])(\d{2})', well_id).group(1, 2)
        row_index = utils.map_letter_to_number(row_name)
        col_index = int(col_name)
        return (row_index, col_index)

    @staticmethod
    def map_well_position_to_id(well_position):
        '''
        Mapping of the one-based index position to the identifier string
        representation.

        Parameters
        ----------
        well_position: Tuple[int]
            one-based row, column position of a given well within the plate

        Returns
        -------
        str
            identifier string representation of a well

        Examples
        --------
        >>>WellPlate.map_well_position_to_id((1, 2))
        "A02"
        '''
        row_index, col_index = well_position[0], well_position[1]
        row_name = utils.map_number_to_letter(row_index)
        return '%s%.2d' % (row_name, col_index)


class Slide(Experiment):

    '''
    A slide represents a single sample that is stained and imaged under the
    same conditions.
    '''

    def __init__(self, experiment_dir, cfg, user_cfg, library):
        '''
        Initialize an instance of class Slide.

        Parameters
        ----------
        experiment_dir: str
            absolute path to experiment folder
        cfg: TmlibConfigurations
            configuration settings for names of directories and files on disk
        library: str
            image library that should be used
            (options: ``"vips"`` or ``"numpy"``)

        See also
        --------
        `tmlib.cfg_setters.TmlibConfiguration`_
        `tmlib.cfg`_
        '''
        super(Slide, self).__init__(
            experiment_dir, cfg, user_cfg, library)
        self.experiment_dir = os.path.expandvars(experiment_dir)
        self.experiment_dir = os.path.expanduser(self.experiment_dir)
        self.experiment_dir = os.path.abspath(self.experiment_dir)
        self.cfg = cfg
        self.user_cfg = cfg
        self.library = library

    @property
    def dimensions(self):
        '''
        Returns
        -------
        Tuple[int]
            ``(1, 1)``
        '''
        self._dimensions = (1, 1)
        return self._dimensions
