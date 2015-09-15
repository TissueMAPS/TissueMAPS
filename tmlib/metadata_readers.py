import bioformats
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
