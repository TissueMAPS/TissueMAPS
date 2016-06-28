'''Implementation of classes for reading microscope image and metadata files
provided in a format specific to the Zeiss AxioImager M2 microscope equipped
with Axiovision software.
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
IMAGE_FILE_REGEX_PATTERN = r'.+_p(?P<s>\d+)(?P<c>[A-Za-z0-9]+)\.'

#: Supported extensions for metadata files
METADATA_FILE_REGEX_PATTERN = r''


class AxioMetadataHandler(MetadataHandler):

    '''Class for handling metadata specific to the Zeiss AxioImager M2
    microsopce with Axiovision software.
    '''

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


class AxioMetadataReader(MetadataReader):

    '''Class for reading metadata from files formats specific to the Zeiss
    AxioImager M2 with Axiovision software.
    '''

    @notimplemented
    def read(self, microscope_metadata_files, microscope_image_files):
