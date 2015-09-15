import bioformats
from .handler import MetadataHandler


class DefaultMetadataHandler(MetadataHandler):

    '''
    Class for handling image metadata in standard cases where additional
    metadata files are not required or not available.
    '''

    def __init__(self, image_files, additional_files, ome_xml_files,
                 cycle_name):
        '''
        Initialize an instance of class MetadataHandler.

        Parameters
        ----------
        image_upload_files: List[str]
            full paths to image files
        additional_files: List[str]
            full paths to additional microscope-specific metadata files
        ome_xml_files: List[str]
            full paths to the XML files that contain the extracted OMEXML data
        cycle_name: str
            name of the cycle, i.e. the name of the folder of the corresponding
            experiment or subexperiment
        '''
        super(DefaultMetadataHandler, self).__init__(
                image_files, additional_files, ome_xml_files, cycle_name)
        self.image_files = image_files
        self.additional_files = additional_files
        self.ome_xml_files = ome_xml_files
        self.cycle_name = cycle_name

    @property
    def ome_additional_metadata(self):
        '''
        Returns
        -------
        bioformats.omexml.OMEXML
            empty object
        '''
        self._ome_additional_metadata = bioformats.OMEXML()
        return self._ome_additional_metadata
