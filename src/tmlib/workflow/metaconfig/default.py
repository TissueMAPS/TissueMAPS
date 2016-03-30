from tmlib.workflow.metaconfig.base import MetadataReader
from tmlib.workflow.metaconfig.base import MetadataHandler
from tmlib.workflow.metaconfig.ome_xml import XML_DECLARATION


#: Regular expression pattern to identify image files
IMAGE_FILE_REGEX_PATTERN = ''  # TODO: read supported formats


class DefaultMetadataHandler(MetadataHandler):

    '''Class for handling image metadata in standard cases where additional
    metadata files are not required or not available.
    '''

    #: Regular expression pattern to identify image files
    IMAGE_FILE_REGEX_PATTERN = IMAGE_FILE_REGEX_PATTERN

    def __init__(self, omexml_images):
        '''
        Parameters
        ----------
        omexml_images: Dict[str, bioformats.omexml.OMEXML]
            metadata extracted from microscope image files
        '''
        super(DefaultMetadataHandler, self).__init__(omexml_images)
