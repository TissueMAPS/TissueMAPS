from .metamorph import MetamorphMetadataHandler


class VisiviewMetadataHandler(MetamorphMetadataHandler):

    '''
    Class for metadata handling specific to microscopes equipped with the
    `VisiView software <http://www.visitron.de/Products/Software/VisiView/visiview.html>`_.
    '''

    REGEXP = ('(?P<cycle_name>.+)_?(?P<well_id>[A-Z]\d{2})?'
              '_(?P<channel_name>\w+)_s(?P<site_id>\d+)_?t?(?P<time_id>\d+)?\.')

    def __init__(self, image_files, additional_files, ome_xml_files,
                 cycle_name):
        '''
        Initialize an instance of class VisiviewMetadataHandler.

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
        super(VisiviewMetadataHandler, self).__init__(
                image_files, additional_files, ome_xml_files, cycle_name)
        self.image_files = image_files
        self.ome_xml_files = ome_xml_files
        self.cycle_name = cycle_name
        self.additional_files = additional_files
