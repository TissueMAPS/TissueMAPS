import bioformats
from .handlers import MetadataHandler
from .readers import MetadataReader


class BioformatsMetadataReader(MetadataReader):

    '''
    `Python-bioformats <https://github.com/CellProfiler/python-bioformats>`_
    provides an interface for reading metadata form files
    using `python-javabridge <https://github.com/CellProfiler/python-javabridge>`_.

    However, this approach often leads to incorrect parsing of metadata.
    Therefore, we decided to extract metadata from the image files directly via
    Bio-Formats using the
    `showinf <http://www.openmicroscopy.org/site/support/bio-formats5.1/users/comlinetools/display.html>`_
    command line tool. This tool prints the OME-XML to standard output, which
    we direct to a file.
    '''

    def read(self, filename):
        '''
        Read Open Microscopy Environment (OME) metadata from XML file on disk.

        Parameters
        ----------
        filename: str
            absolute path to the file

        Returns
        -------
        bioformats.omexml.OMEXML
            image metadata

        Raises
        ------
        NotSupportedError
            when the file format is not supported
        '''
        # ome_xml_data = bf.get_omexml_metadata(filename)
        with open(filename, 'r') as f:
            ome_xml_data = f.read()
        metadata = bioformats.OMEXML(ome_xml_data)
        return metadata


class BioformatsMetadataHandler(MetadataHandler):

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
        super(BioformatsMetadataReader, self).__init__(
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
