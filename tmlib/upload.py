import os
import logging
import bioformats
from cached_property import cached_property
from natsort import natsorted
from .metadata import ImageFileMapper
from .formats import Formats
from .readers import XmlReader
from .readers import JsonReader

logger = logging.getLogger(__name__)


class Upload(object):
    '''
    Class that serves as a container for uploaded files.
    '''
    def __init__(self, upload_subdir, cfg, user_cfg):
        '''
        Initialize an instance of class Cycle.

        Parameters
        ----------
        upload_subdir: str
            absolute path to the directory that contains uploaded files
        cfg: TmlibConfigurations
            configuration settings for names of directories and files on disk
        user_cfg: Dict[str, str]
            additional user configuration settings

        Raises
        ------
        OSError
            when `upload_subdir` does not exist
        '''
        self.upload_subdir = upload_subdir
        if not os.path.exists(self.upload_subdir):
            raise OSError('Upload sub-directory does not exist.')
        self.cfg = cfg
        self.user_cfg = user_cfg

    @property
    def name(self):
        '''
        Returns
        -------
        str
            name of the upload folder
        '''
        return os.path.basename(os.path.abspath(self.upload_subdir))

    @property
    def dir(self):
        '''
        Returns
        -------
        str
            absolute path to the upload folder
        '''
        return self.upload_subdir

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
        self._image_dir = self.cfg.IMAGE_UPLOAD_DIR.format(
                                                upload_subdir=self.dir,
                                                sep=os.path.sep)
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
        self._additional_dir = self.cfg.ADDITIONAL_UPLOAD_DIR.format(
                                                upload_subdir=self.dir,
                                                sep=os.path.sep)
        if not os.path.exists(self._additional_dir):
            logger.debug('create directory for additional file uploads: %s'
                         % self._additional_dir)
            os.mkdir(self._additional_dir)
        return self._additional_dir

    @cached_property
    def ome_xml_dir(self):
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
        self._ome_xml_dir = self.cfg.OME_XML_DIR.format(
                                                upload_subdir=self.dir,
                                                sep=os.path.sep)
        if not os.path.exists(self._ome_xml_dir):
            logger.debug('create directory for ome xml files: %s'
                         % self._ome_xml_dir)
            os.mkdir(self._ome_xml_dir)
        return self._ome_xml_dir

    @cached_property
    def ome_xml_files(self):
        '''
        Returns
        -------
        List[str]
            names of *OMEXML* files in `ome_xml_dir`

        Raises
        ------
        OSError
            when no XML files are found in `ome_xml_dir`
        '''
        files = [
            f for f in os.listdir(self.ome_xml_dir)
            if f.endswith('.ome.xml')
        ]
        files = natsorted(files)
        if not files:
            raise OSError('No XML files found in "%s"' % self.ome_xml_dir)
        self._ome_xml_files = files
        return self._ome_xml_files

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
