import os
import re
import logging
import bioformats
from cached_property import cached_property
from natsort import natsorted
from . import utils
from .metadata import ImageFileMapper
from .formats import Formats
from .readers import XmlReader
from .readers import JsonReader
from .errors import RegexpError

logger = logging.getLogger(__name__)


class Upload(object):
    '''
    Class that serves as a container for uploaded files belonging to one
    *plate*.
    '''
    def __init__(self, upload_dir, cfg, user_cfg):
        '''
        Initialize an instance of class Cycle.

        Parameters
        ----------
        upload_dir: str
            absolute path to the directory that contains uploaded files
        cfg: TmlibConfigurations
            configuration settings for names of directories and files on disk
        user_cfg: Dict[str, str]
            additional user configuration settings

        Raises
        ------
        OSError
            when `upload_dir` does not exist
        '''
        self.upload_dir = upload_dir
        if not os.path.exists(self.upload_dir):
            raise OSError('Upload sub-directory does not exist.')
        self.cfg = cfg
        self.user_cfg = user_cfg

    @property
    def dir(self):
        '''
        Returns
        -------
        str
            absolute path to the upload folder
        '''
        return self.upload_dir

    @property
    def name(self):
        '''
        Returns
        -------
        str
            name of the upload folder
        '''
        return os.path.basename(self.upload_dir)

    @property
    def plate_name(self):
        '''
        Returns
        -------
        str
            name of the corresponding plate
        '''
        regexp = utils.regex_from_format_string(self.cfg.UPLOAD_DIR)
        match = re.search(regexp, self.name)
        if not match:
            raise RegexpError(
                    'Can\'t determine cycle id number from folder "%s" '
                    'using format "%s" provided by the configuration settings.'
                    % (self.name, self.cfg.CYCLE_DIR))
        self._plate_name = match.group('plate_name')
        return self._plate_name

    def _is_upload_subdir(self, folder):
        format_string = self.cfg.UPLOAD_SUBDIR
        regexp = utils.regex_from_format_string(format_string)
        return True if re.match(regexp, folder) else False

    @property
    def subuploads(self):
        '''
        Returns
        -------
        List[UploadedPlate]
            containers for uploaded files that belong to one *plate*
        '''
        upload_subdirs = [
            os.path.join(self.dir, d)
            for d in os.listdir(self.dir)
            if os.path.isdir(os.path.join(self.dir, d))
            and self._is_upload_subdir(d)
        ]
        upload_subdirs = natsorted(upload_subdirs)
        self._uploaded_plates = [
                SubUpload(d, self.cfg, self.user_cfg)
                for d in upload_subdirs
            ]
        return self._uploaded_plates

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
        return os.path.join(self.dir, 'image_file_mapper.json')

    @property
    def image_mapper(self):
        '''
        Returns
        -------
        List[ImageFileMapper]
            key-value pairs to map the location of individual planes within the
            original files to the *Image* elements in the OMEXML
        '''
        self._image_mapper = list()
        with JsonReader(self.dir) as reader:
            hashmap = reader.read(self.image_mapper_file)
        for element in hashmap:
            self._image_mapper.append(ImageFileMapper.set(element))
        return self._image_mapper


class SubUpload(object):

    def __init__(self, subupload_dir, cfg, user_cfg):
        '''
        Parameters
        ----------
        subupload_dir: str
            absolute path to the subupload folder
        '''
        self.subupload_dir = subupload_dir
        self.cfg = cfg
        self.user_cfg = user_cfg

    @property
    def dir(self):
        '''
        Returns
        -------
        str
            absolute path to the subupload folder
        '''
        return self.subupload_dir

    @property
    def name(self):
        '''
        Returns
        -------
        str
            name of the subupload folder
        '''
        return os.path.basename(self.dir)

    @cached_property
    def image_dir(self):
        '''
        Returns
        -------
        str
            absolute path to directory that contains the uploaded images

        Note
        ----
        Creates the directory if it doesn't exist.
        '''
        self._image_dir = self.cfg.UPLOAD_IMAGE_DIR.format(
                                upload_subdir=self.dir, sep=os.path.sep)
        if not os.path.exists(self._image_dir):
            logger.debug('create directory for image file uploads: %s'
                         % self._image_dir)
            os.mkdir(self._image_dir)
        return self._image_dir

    @cached_property
    def additional_dir(self):
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
        self._additional_dir = self.cfg.UPLOAD_ADDITIONAL_DIR.format(
                                upload_subdir=self.dir, sep=os.path.sep)
        if not os.path.exists(self._additional_dir):
            logger.debug('create directory for additional file uploads: %s'
                         % self._additional_dir)
            os.mkdir(self._additional_dir)
        return self._additional_dir

    @cached_property
    def omexml_dir(self):
        '''
        Returns
        -------
        str
            absolute path to directory that contains the extracted OMEXML files
            for each uploaded image in `image_dir`

        Note
        ----
        Creates the directory if it doesn't exist.
        '''
        self._omexml_dir = self.cfg.UPLOAD_OMEXML_DIR.format(
                                upload_subdir=self.dir, sep=os.path.sep)
        if not os.path.exists(self._omexml_dir):
            logger.debug('create directory for ome xml files: %s'
                         % self._omexml_dir)
            os.mkdir(self._omexml_dir)
        return self._omexml_dir

    @cached_property
    def omexml_files(self):
        '''
        Returns
        -------
        List[str]
            names of *OMEXML* files in `omexml_dir`

        Raises
        ------
        OSError
            when no XML files are found in `omexml_dir`
        '''
        files = [
            f for f in os.listdir(self.omexml_dir)
            if f.endswith('.ome.xml')
        ]
        files = natsorted(files)
        if not files:
            raise OSError('No XML files found in "%s"' % self.omexml_dir)
        self._omexml_files = files
        return self._omexml_files

    @cached_property
    def image_files(self):
        '''
        Returns
        -------
        List[str]
            names of image files in `image_dir`

        Warning
        -------
        Only files with supported file extensions are considered.

        See also
        --------
        `formats.Formats`_
        '''
        self._image_files = [
            f for f in os.listdir(self.image_dir)
            if not os.path.isdir(os.path.join(self.image_dir, f))
            and os.path.splitext(f)[1] in Formats().supported_extensions
        ]
        return self._image_files

    @cached_property
    def additional_files(self):
        '''
        Returns
        -------
        List[str]
            names of files in `additional_dir`
        '''
        self._additional_files = [
            f for f in os.listdir(self.additional_dir)
            if not os.path.isdir(os.path.join(self.additional_dir, f))
        ]
        return self._additional_files

    @property
    def image_metadata_file(self):
        '''
        Returns
        -------
        str
            name of the file that contains image related metadata
        '''
        return 'configured_metadata.ome.xml'

    @property
    def image_metadata(self):
        '''
        Returns
        -------
        bioformats.OMEXML
            configured image metadata
        '''
        with XmlReader(self.dir) as reader:
            omexml = reader.read(self.image_metadata_file)
        self._image_metadata = bioformats.OMEXML(omexml)
        return self._image_metadata

    @property
    def image_mapper_file(self):
        '''
        Returns
        -------
        str
            name of the file that contains key-value pairs for mapping
            the images stored in the original image files to the
            the OME *Image* elements in `image_metadata`
        '''
        return 'image_file_mapper.json'

    @property
    def image_mapper(self):
        '''
        Returns
        -------
        List[ImageFileMapper]
            key-value pairs to map the location of individual planes within the
            original files to the *Image* elements in the OMEXML
        '''
        self._image_mapper = list()
        with JsonReader(self.dir) as reader:
            hashmap = reader.read(self.image_mapper_file)
        for element in hashmap:
            self._image_mapper.append(ImageFileMapper.set(element))
        return self._image_mapper
