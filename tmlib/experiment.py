import re
import os
import logging
import numpy as np
from natsort import natsorted
from cached_property import cached_property
from . import config
from . import utils
from .plate import Plate
from .upload import Upload
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
        # Check that `experiment_dir` is actually the root directory
        # of an experiment
        if not os.path.exists(self.user_cfg_file):
            raise ValueError(
                'The provided directory is not a valid experiment root folder')
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
        Returns
        -------
        Experiment
            object configured with default settings
        '''
        logger.debug('using the "%s" image library', self.library)
        return Experiment(
                    self.experiment_dir, self.cfg, self.user_cfg, self.library)


class Experiment(object):
    '''
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

    @cached_property
    def plates_dir(self):
        '''
        Returns
        -------
        str
            absolute path to the *plates* subdirectory

        Note
        ----
        Creates the directory if it doesn't exist.
        '''
        self._plates_dir = self.cfg.PLATES_DIR.format(
                                experiment_dir=self.dir, sep=os.path.sep)
        if not os.path.exists(self._plates_dir):
            logger.debug('create directory for plates: %s', self._plates_dir)
            os.mkdir(self._plates_dir)
        return self._plates_dir

    def _is_plate_dir(self, folder):
        format_string = self.cfg.PLATE_DIR
        regexp = utils.regex_from_format_string(format_string)
        return True if re.match(regexp, folder) else False

    @property
    def plates(self):
        '''
        Returns
        -------
        List[Plate]
            configured plate objects (the exact subtype depends on the user
            configuration settings, e.g. `WellPlate` or `Slide`)
        '''
        plate_dirs = [
            os.path.join(self.plates_dir, d)
            for d in os.listdir(self.plates_dir)
            if os.path.isdir(os.path.join(self.plates_dir, d))
            and not d.startswith('.')
        ]
        plate_dirs = natsorted(plate_dirs)
        self._plates = [
                Plate(d, self.cfg, self.user_cfg, self.library)
                for d in plate_dirs
            ]
        return self._plates

    @property
    def uploads_dir(self):
        '''
        Returns
        -------
        str
            absolute path to the *uploads* subdirectory, where uploaded files
            are located

        Raises
        ------
        OSError
            when `uploads_dir` does not exist

        Note
        ----
        Each *plate* is uploaded into a separate subfolder of `uploads_dir`.
        '''
        self._uploads_dir = self.cfg.UPLOADS_DIR.format(
                                experiment_dir=self.dir, sep=os.path.sep)
        if not os.path.exists(self._uploads_dir):
            raise OSError('Uploads directory does not exist')
        return self._uploads_dir

    def _is_upload_dir(self, folder):
        format_string = self.cfg.UPLOAD_DIR
        regexp = utils.regex_from_format_string(format_string)
        return True if re.match(regexp, folder) else False

    @property
    def uploads(self):
        '''
        The user can upload image files and optionally additional metadata
        files. If the experiment consists of multiple *plates*, the files
        for each plate are uploaded individually and stored in separate
        upload folders. Each *plate* can itself contain multiple *cycles*.

        Returns
        -------
        List[UploadContainer]
            configured upload objects

        See also
        --------
        `tmlib.upload.Upload`_
        `tmlib.upload.UploadedPlate`_
        `tmlib.config`_

        Note
        ----
        All *plates* belonging to one experiment must have the same format, e.g.
        all 384-well plates.
        '''
        upload_dirs = natsorted([
            os.path.join(self.uploads_dir, d)
            for d in os.listdir(self.uploads_dir)
            if os.path.isdir(os.path.join(self.uploads_dir, d))
            and self._is_upload_dir(d)
        ])
        self._uploads = [
            Upload(d, self.cfg, self.user_cfg) for d in upload_dirs
        ]
        return self._uploads

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
                                experiment_dir=self.dir, sep=os.path.sep)
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
            with the same *channel_ix*, *zplane_ix* and *tpoint_ix*

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
            for plate in self.plates:
                for cycle in plate.cycles:
                    md = cycle.image_metadata_table
                    channels = np.unique(md['channel_ix'])
                    zplanes = np.unique(md['zplane_ix'])
                    for c in channels:
                        for z in zplanes:
                            k = (cycle.index, c, z)
                            self._layer_names[k] = self.cfg.LAYER_NAME.format(
                                experiment_name=self.name,
                                t=cycle.index, c=c, z=z)
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
                    and img.metadata.zplane_ix == p
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
                                experiment_name=self.name, sep=os.path.sep)
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
                md.site_ix
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
                md.zplane_ix
                for cycle in self.cycles
                for md in cycle.image_metadata
        ])
        return self._focal_planes

    # def dump_metadata(self):
    #     experiment_e = etree.Element('experiment')
    #     experiment_e.set('name', self.name)

    #     cycles_e = etree.SubElement(experiment_e, 'cycles')

    #     for cycle in self.cycles:
    #         cycle_e = etree.SubElement(cycles_e, 'cycle')
    #         cycle_e.set('name', cycle.name)
    #         cycle_e.set('index', str(cycle.index))

    #         images_e = etree.SubElement(cycle_e, 'images')
    #         for i, md in enumerate(cycle.image_metadata):
    #             file_e = etree.SubElement(images_e, 'file')
    #             file_e.set('name', md.name)
    #             file_e.set('site_ix', str(md.site_ix))
    #             file_e.set('zplane_ix', str(md.zplane_ix))
    #             file_e.set('channel_ix', str(md.channel_name))
    #             file_e.set('source_file_id', str(md.original_filename))

    #         acq_sites_e = etree.SubElement(cycle_e, 'acquisition_sites')
    #         acq_sites_e.set('upper_overhang', str(md.upper_overhang))
    #         acq_sites_e.set('lower_overhang', str(md.lower_overhang))
    #         acq_sites_e.set('left_overhang', str(md.left_overhang))
    #         acq_sites_e.set('right_overhang', str(md.right_overhang))
    #         sites = [md.site for md in cycle.image_metadata]
    #         for i, s in enumerate(self.acquisition_sites):
    #             ix = sites.index(s)
    #             md = cycle.image_metadata[ix]
    #             site_e = etree.SubElement(acq_sites_e, 'site')
    #             site_e.set('id', str(i+1))
    #             site_e.set('y_shift', str(md.y_shift))
    #             site_e.set('x_shift', str(md.x_shift))
    #             site_e.set('well_id', str(md.well_id))
    #             site_e.set('row_index', str(md.row_index))
    #             site_e.set('col_index', str(md.col_index))

    #         channels_e = etree.SubElement(cycle_e, 'channels')
    #         for i, c in enumerate(cycle.channels):
    #             channel_e = etree.SubElement(channels_e, 'channel')
    #             channel_e.set('id', str(i+1))
    #             channel_e.set('name', c)

    #         focal_planes_e = etree.SubElement(cycle_e, 'focal_planes')
    #         for i, p in enumerate(self.focal_planes):
    #             plane_e = etree.SubElement(focal_planes_e, 'plane')
    #             plane_e.set('id', str(i+1))

    #     uploads_e = etree.SubElement(experiment_e, 'uploads')
    #     # TODO

    #     print etree.tostring(experiment_e, pretty_print=True,
    #                          xml_declaration=True)

    #     doc = etree.ElementTree(experiment_e)
    #     with open(os.path.join(self.dir, self.metadata_file), 'w') as f:
    #         doc.write(f, pretty_print=True, xml_declaration=True)
