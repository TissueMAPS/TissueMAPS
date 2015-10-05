import os
import bioformats
from lxml import etree
from .default import MetadataHandler
from ..readers import MetadataReader
from ..illuminati import stitch


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

    Note
    ----
    The OME schema doesn't provide information about wells at the individual
    *Image* level: see `OME data model <http://www.openmicroscopy.org/Schemas/Documentation/Generated/OME-2015-01/ome.html>`_.
    Instead, it provides a *Plate* element, which contains *Well* elements.
    *Well* elements contain the positional information, such as row and
    column index of each well within the plate. The *WellSample* elements
    represent individual image acquisition sites within a well and can hold
    metadata, such as the x and y stage positions. In addition, there is an
    *ImageRef* element, which can be used to map a *WellSample* to an
    individual *Image* element.
    However, the Yokogawa microscope stores all well information per
    individual image file (which makes more sense if you ask me).
    Therefore, we have to first create a *Plate* object in order to be able to
    store well information in the OMEXML schema and then later extract this
    information from the *Plate* element and map it back to individual *Image*
    or *Plane* elements. This results in a lot of recursive indexing,
    but we'll stick to it for sake of Bio-Formats compatibility.

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
        metadata = bioformats.OMEXML()
        # 1) Obtain the positional information for each image acquisition site
        #    from the ".mlf" file:
        mlf_tree = etree.parse(mlf_filename)
        mlf_root = mlf_tree.getroot()
        mlf_elements = mlf_root.xpath('.//bts:MeasurementRecord',
                                      namespaces=mlf_root.nsmap)
        mlf_ns = mlf_root.nsmap['bts']

        metadata.image_count = len(mlf_elements)
        well_info = list()
        for i, e in enumerate(mlf_elements):
            metadata.image(i).Name = e.text
            pixels = metadata.image(i).Pixels
            pixels.SizeT = 1
            pixels.SizeC = 1
            pixels.SizeZ = 1
            pixels.plane_count = 1
            pixels.Plane(0).TheT = 0
            pixels.Plane(0).TheZ = 0
            pixels.Plane(0).TheC = 0  # this is what most microscopes do
            if e.attrib['{%s}Type' % mlf_ns] == 'IMG':
                pixels.Channel(0).Name = e.attrib['{%s}Ch' % mlf_ns]
            else:
                # In case of "ERR" the channel information is not provided
                pixels.Channel(0).Name = None
            pixels.Plane(0).PositionX = float(e.attrib['{%s}X' % mlf_ns])
            pixels.Plane(0).PositionY = float(e.attrib['{%s}Y' % mlf_ns])
            well_info.append({
                'well_index': int(e.attrib['{%s}FieldIndex' % mlf_ns]),
                'well_position': (int(e.attrib['{%s}Row' % mlf_ns]),
                                  int(e.attrib['{%s}Column' % mlf_ns]))
            })

        # 2) Obtain the general experiment information and well plate format
        #    specifications from the ".mrf" file and store them in the OMEXML
        #    object as well:
        mrf_tree = etree.parse(mrf_filename)
        mrf_root = mrf_tree.getroot()
        mrf_ns = mrf_root.nsmap['bts']
        e = mrf_root
        name = e.attrib['{%s}Title' % mrf_ns]
        plate = metadata.PlatesDucktype(metadata.root_node).newPlate(name=name)
        plate.RowNamingConvention = 'number'
        plate.ColumnNamingConvention = 'number'
        plate.Rows = e.attrib['{%s}RowCount' % mrf_ns]
        plate.Columns = e.attrib['{%s}ColumnCount' % mrf_ns]
        wells = [wi['well_position'] for wi in well_info]
        for w in set(wells):
            # Create a "Well" instance for each imaged well in the plate
            row_index = w[0]  # TODO: should this be zero-based?
            col_index = w[1]
            well = metadata.WellsDucktype(plate).new(row=row_index,
                                                     column=col_index)
            well_samples = metadata.WellSampleDucktype(well.node)
            well_sample_indices = [wi['well_index'] for wi in well_info
                                   if wi['well_position'] == w]
            for s in set(well_sample_indices):
                file_indices = [i for i, x in enumerate(well_info)
                                if x['well_index'] == s
                                and x['well_position'] == w]
                i = file_indices[0]  # they were all acquired at the same site
                # Create a "WellSample" instance for each acquisition site
                ix = s-1  # zero-based
                well_samples.new(index=ix)
                # Store positional information for each acquisition site
                well_samples[ix].PositionX = \
                    metadata.image(i).Pixels.Plane(0).PositionX
                well_samples[ix].PositionY = \
                    metadata.image(i).Pixels.Plane(0).PositionY
                # Provide the names of the reference images that are located
                # at this WellSample index position
                filenames = [metadata.image(i).Name for i in file_indices]
                well_samples[ix].ImageRef = {r'(.*)': filenames}

        return metadata


class CellvoyagerMetadataHandler(MetadataHandler):

    '''
    Class for reading additional metadata files specific to the Yokogawa
    Cellvoyager 7000 microscope.
    '''

    SUPPORTED_FILE_EXTENSIONS = {'.mlf', '.mrf'}

    REGEXP_PATTERN = ''

    def __init__(self, image_files, additional_files, ome_xml_files,
                 cycle_name):
        '''
        Instantiate an instance of class MetadataHandler.

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
        super(CellvoyagerMetadataHandler, self).__init__(
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
            raise OSError('%d metadata files are required: "%s"'
                          % (len(self.SUPPORTED_FILE_EXTENSIONS),
                             '", "'.join(self.SUPPORTED_FILE_EXTENSIONS)))
        mlf_file = [f for f in files if f.endswith('.mlf')][0]
        mrf_file = [f for f in files if f.endswith('.mrf')][0]
        with CellvoyagerMetadataReader() as reader:
            self._ome_additional_metadata = reader.read(mlf_file, mrf_file)
        return self._ome_additional_metadata

    @staticmethod
    def _calculate_coordinates(positions):
        # y axis is inverted
        coordinates = stitch.calc_image_coordinates(
                        positions, reverse_rows=True)
        return coordinates
