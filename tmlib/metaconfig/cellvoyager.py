import os
import re
import logging
import bioformats
from collections import defaultdict
from cached_property import cached_property
from lxml import etree
from .ome_xml import XML_DECLARATION
from .default import MetadataHandler
from .. import utils
from ..readers import MetadataReader
from ..illuminati import stitch

logger = logging.getLogger(__name__)


class CellvoyagerMetadataReader(MetadataReader):

    '''
    Class for reading metadata from files formats specific to the Yokogawa
    CellVoyager 7000 microscope.

    Yokogawa doesn't store the position and channel information at the level
    of individual images, but in additional metadata files with *.mlf* and
    *.mrf* extensions.
    Unfortunately, these file formats are not supported by Bio-Formats,
    see `CellVoyagerReader <http://www.openmicroscopy.org/site/support/bio-formats5.1/formats/cellvoyager.html>`_.
    For compatibility with the OME data model, the `CellvoyagerMetadataReader`
    reads the XML from "MeasurementDetail.mrf" and "MeasurmentData.mlf" files,
    extracts the relevant data and stores them in an OMEXML object according to
    the Bio-Formats convention.

    Examples
    --------
    >>> mlf_filename = '/path/to/metadata/MeasurementData.mlf'
    >>> mrf_filename = '/path/to/metadata/MeasurementDetail.mrf'
    >>> with CellvoyagerReader() as reader:
    ...     metadata = reader.read(mlf_filename, mrf_filename)
    >>> type(metadata)
    bioformats.omexml.OMEXML
    '''

    def read(self, mlf_filename, mrf_filename):
        '''
        Read metadata from vendor specific files on disk.

        Parameters
        ----------
        mlf_filename: str
            absolute path to the *.mlf* file
        mrf_filename: str
            absolute path to the *.mrf* file

        Returns
        -------
        bioformats.omexml.OMEXML
            image and plate metadata
        '''
        metadata = bioformats.OMEXML(XML_DECLARATION)
        # 1) Obtain the positional information for each image acquisition site
        #    from the ".mlf" file:
        mlf_tree = etree.parse(mlf_filename)
        mlf_root = mlf_tree.getroot()
        mlf_elements = mlf_root.xpath('.//bts:MeasurementRecord',
                                      namespaces=mlf_root.nsmap)
        mlf_ns = mlf_root.nsmap['bts']

        metadata.image_count = len(mlf_elements)
        lut = defaultdict(list)
        r = re.compile(CellvoyagerMetadataHandler.REGEX)
        for i, e in enumerate(mlf_elements):
            img = metadata.image(i)
            # A name has to be set as a flag for the handler to update
            # the metadata
            img.Name = e.text
            # TODO: there is a bug that prevents setting the date for
            # images with index > 0
            img.AcquisitionDate = e.attrib['{%s}Time' % mlf_ns]
            # Image files always contain only a single plane
            img.Pixels.SizeT = 1
            img.Pixels.SizeC = 1
            img.Pixels.SizeZ = 1
            img.Pixels.plane_count = 1
            if e.attrib['{%s}Type' % mlf_ns] == 'IMG':
                img.Pixels.Channel(0).Name = e.attrib['{%s}Ch' % mlf_ns]
            else:
                logger.error('erroneous acquisition - no channel information '
                             'available for image "%s"', img.Name)
                img.Pixels.Channel(0).Name = None
            img.Pixels.Plane(0).PositionX = float(e.attrib['{%s}X' % mlf_ns])
            img.Pixels.Plane(0).PositionY = float(e.attrib['{%s}Y' % mlf_ns])

            matches = r.search(img.Name)
            captures = matches.groupdict()
            well_row = utils.map_number_to_letter(
                            int(e.attrib['{%s}Row' % mlf_ns]))
            well_col = int(e.attrib['{%s}Column' % mlf_ns])
            well_id = '%s%.2d' % (well_row, well_col)
            lut[well_id].append(captures)

        # 2) Obtain the general experiment information and well plate format
        #    specifications from the ".mrf" file and store them in the OMEXML
        #    object as well:
        mrf_tree = etree.parse(mrf_filename)
        mrf_root = mrf_tree.getroot()
        mrf_ns = mrf_root.nsmap['bts']
        e = mrf_root
        name = e.attrib['{%s}Title' % mrf_ns]
        plate = metadata.PlatesDucktype(metadata.root_node).newPlate(name=name)
        plate.RowNamingConvention = 'letter'
        plate.ColumnNamingConvention = 'number'
        plate.Rows = e.attrib['{%s}RowCount' % mrf_ns]
        plate.Columns = e.attrib['{%s}ColumnCount' % mrf_ns]
        wells = lut.keys()
        for w in set(wells):
            # Create a *Well* element for each imaged well in the plate
            row = utils.map_letter_to_number(w[0]) - 1
            col = int(w[1:]) - 1
            well = metadata.WellsDucktype(plate).new(row=row, column=col)
            well_samples = metadata.WellSampleDucktype(well.node)
            for i, reference in enumerate(lut[w]):
                # Create a *WellSample* element for each acquisition site
                well_samples.new(index=i)
                well_samples[i].ImageRef = reference

        return metadata


class CellvoyagerMetadataHandler(MetadataHandler):

    '''
    Class for metadata handling specific to the Yokogawa Cellvoyager 7000
    microscope.
    '''

    SUPPORTED_FILE_EXTENSIONS = {'.mlf', '.mrf'}

    REGEX = ('[^_]+_(?P<w>[A-Z]\d{2})_T(?P<t>\d+)'
             'F(?P<s>\d+)L\d+A\d+Z(?P<z>\d+)C(?P<c>\d+)\.')

    def __init__(self, image_files, additional_files, omexml_files,
                 plate_name):
        '''
        Initialize an instance of class MetadataHandler.

        Parameters
        ----------
        image_files: List[str]
            full paths to image files
        additional_files: List[str]
            full paths to additional microscope-specific metadata files
        omexml_files: List[str]
            full paths to the XML files that contain the extracted OMEXML data
        plate_name: str
            name of the corresponding plate
        '''
        super(CellvoyagerMetadataHandler, self).__init__(
                image_files, additional_files, omexml_files, plate_name)
        self.image_files = image_files
        self.additional_files = additional_files
        self.omexml_files = omexml_files
        self.plate_name = plate_name

    @cached_property
    def ome_additional_metadata(self):
        '''
        Returns
        -------
        bioformats.omexml.OMEXML
            metadata retrieved from Yokogawa microscope-specific files

        See also
        --------
        `CellvoyagerMetadataReader`_
        '''
        files = [
            f for f in self.additional_files
            if os.path.splitext(f)[1] in self.SUPPORTED_FILE_EXTENSIONS
        ]
        if len(files) != len(self.SUPPORTED_FILE_EXTENSIONS):
            logger.warning('%d metadata files would be required: "%s"'
                           % (len(self.SUPPORTED_FILE_EXTENSIONS),
                              '", "'.join(self.SUPPORTED_FILE_EXTENSIONS)))
            self._ome_additional_metadata = bioformats.OMEXML(XML_DECLARATION)
            # Add an empty *Plate* element
            self._ome_additional_metadata.PlatesDucktype(
                        self._ome_additional_metadata.root_node).newPlate(
                        name='default')
        else:
            mlf_file = [f for f in files if f.endswith('.mlf')][0]
            mrf_file = [f for f in files if f.endswith('.mrf')][0]
            logger.info('read metadata from provided files')
            with CellvoyagerMetadataReader() as reader:
                self._ome_additional_metadata = reader.read(mlf_file, mrf_file)
        return self._ome_additional_metadata

    @staticmethod
    def _calculate_coordinates(positions):
        # y axis is inverted
        logger.debug('flip y axis for calculation of grid coordinates')
        coordinates = stitch.calc_grid_coordinates_from_positions(
                        positions, reverse_rows=True)
        return coordinates
