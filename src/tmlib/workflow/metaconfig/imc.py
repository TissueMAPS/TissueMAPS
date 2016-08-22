'''Implementation of classes for reading "microscope" image and metadata files
provided in a format specific to the Imaging Mass Cytometer.
'''
import re
import logging
import bioformats
from collections import defaultdict
from lxml import etree

from tmlib.utils import notimplemented
from tmlib.workflow.illuminati import stitch
from tmlib.workflow.metaconfig.base import MetadataReader
from tmlib.workflow.metaconfig.base import MetadataHandler
from tmlib.workflow.metaconfig.omexml import XML_DECLARATION

logger = logging.getLogger(__name__)

#: Regular expression pattern to identify image files
IMAGE_FILE_REGEX_PATTERN = r'[^_]+_.*\((?P<c>.*)\).*tiff'

#: Supported extensions for metadata files
METADATA_FILE_REGEX_PATTERN = r'(?!.*)'


class ImcMetadataHandler(MetadataHandler):

    '''Class for handling metadata specific to the Image Mass Cytometer.'''

    #: Regular expression pattern to identify image files
    IMAGE_FILE_REGEX_PATTERN = IMAGE_FILE_REGEX_PATTERN

    def __init__(self, omexml_images, omexml_metadata=None):
        '''
        Parameters
        ----------
        omexml_images: Dict[str, bioformats.omexml.OMEXML]
            metadata extracted from microscope image files
        omexml_metadata: bioformats.omexml.OMEXML
            metadata extracted from microscope metadata files 
        '''
        super(AxioMetadataHandler, self).__init__(
            omexml_images, omexml_metadata
        )


class ImcMetadataReader(MetadataReader):

    '''Class for reading metadata from files formats specific to the Image
    Mass Cytometer.

    Note
    ----
    The mass cytometer doesn't provide any metadata files.
    '''

    def read(self, microscope_metadata_files, microscope_image_files):
        '''Provides an empty OMEXML.

        Parameters
        ----------
        microscope_metadata_files: List[str]
            absolute path to the microscope metadata files
        microscope_image_files: List[str]
            absolute path to the microscope image files

        Returns
        -------
        bioformats.omexml.OMEXML
            OMEXML image metadata
        '''
        return bioformats.OMEXML(XML_DECLARATION)

