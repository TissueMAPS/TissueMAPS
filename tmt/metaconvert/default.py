import bioformats
from .handler import MetadataHandler


class DefaultMetadataHandler(MetadataHandler):

    '''
    Class for handling image metadata in standard cases where additional
    metadata files are not required or not available.
    '''

    def __init__(self, image_upload_dir, additional_upload_dir, ome_xml_dir,
                 cycle_name):
        '''
        Initialize an instance of class MetadataHandler.

        Parameters
        ----------
        image_upload_dir: str
            directory where image files were uploaded to
        additional_upload_dir: str
            directory where additional microscope-specific metadata files
            may have been uploaded to
        ome_xml_dir: str
            directory where OMEXML metadata files were stored upon extraction
            of metadata from the image files in `image_upload_dir`
        cycle_name: str
            name of the cycle, i.e. the name of the folder of the corresponding
            experiment or subexperiment
        '''
        super(DefaultMetadataHandler, self).__init__(
            image_upload_dir, additional_upload_dir, ome_xml_dir, cycle_name)
        self.image_upload_dir = image_upload_dir
        self.additional_upload_dir = additional_upload_dir
        self.ome_xml_dir = ome_xml_dir
        self.cycle_name = cycle_name

    @property
    def additional_files(self):
        '''
        Returns
        -------
        None
        '''
        self._additional_files = None
        return self._additional_files

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
