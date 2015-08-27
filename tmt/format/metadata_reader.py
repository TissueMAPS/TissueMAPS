from abc import ABCMeta
from abc import abstractmethod
import sys
import os
import re
import traceback
import openslide
import bioformats as bf
from lxml import etree
from ..errors import NotSupportedError


class MetadataReader(object):

    '''
    Abstract base class for reading metadata from additional (non-image) files.

    They return metadata as OMEXML objects, according to the OME data model,
    see `python-bioformats <http://pythonhosted.org/python-bioformats/#metadata>`_.

    Unfortunately, the documentation is very sparse.
    If you need additional information, refer to the relevant
    `source code <https://github.com/CellProfiler/python-bioformats/blob/master/bioformats/omexml.py>`_.

    Warning
    -------
    The image count has to match the number of final image
    '''

    __metaclass__ = ABCMeta

    def __enter__(self):
        return self

    @abstractmethod
    def read(self, filename):
        pass

    def __exit__(self, except_type, except_value, except_trace):
        if except_value:
            sys.stdout.write('The following error occurred:\n%s'
                             % str(except_value))
            for tb in traceback.format_tb(except_trace):
                sys.stdout.write(tb)


class OmeMetadataReader(MetadataReader):

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
        metadata = bf.OMEXML(ome_xml_data)
        return metadata


class OpenslideMetadataReader(MetadataReader):

    def read(self, filename):
        '''
        Read metadata from whole slide images.

        For details on reading metadata via openslide from Python, see
        `online documentation <http://openslide.org/api/python/>`_.

        Parameters
        ----------
        filename: str
            absolute path to the file

        Returns
        -------
        openslide.OpenSlide
            image metadata

        Raises
        ------
        NotSupportedError
            when the file format is not supported
        '''
        metadata = openslide.OpenSlide(filename)
        return metadata

    def __exit__(self, except_type, except_value, except_trace):
        if except_type is openslide.OpenSlideUnsupportedFormatError:
            raise NotSupportedError('File format is not supported.')
        if except_type is openslide.OpenSlideError:
            sys.stdout.write('The following error occurred:\n%s'
                             % str(except_value))
            for tb in traceback.format_tb(except_trace):
                sys.stdout.write(tb)


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
    The *Well* elements contain the positional information, such as row and
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
        metadata = bf.OMEXML()
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
            well = metadata.WellsDucktype(plate).new(row=w[0], column=w[1])
            well_samples = metadata.WellSampleDucktype(well.node)
            well_sample_indices = [wi['well_index'] for wi in well_info
                                   if wi['well_position'] == w]
            for s in set(well_sample_indices):
                image_indices = [i for i, x in enumerate(well_info)
                                 if x['well_index'] == s
                                 and x['well_position'] == w]
                i = image_indices[0]  # they were all acquired at the same site
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
                filenames = [metadata.image(i).Name for i in image_indices]
                well_samples[ix].ImageRef = filenames

        return metadata


class MetamorphMetadataReader(MetadataReader):

    '''
    Class for reading metadata from files formats specific to microscopes
    equipped with Metamorph or Visitron microscopes.

    Warning
    -------
    These formats are generally supported by Bio-Formats. However, by default
    Bio-Formats reads metadata for all files simultaneously using both the
    *.nd* as well as the "*.stk" files. This breaks the logic of individual
    file reading and can only be prevented by separating the *.nd* file from
    the *.stk* files, i.e. placing them into separate folders.
    However, this in turn prevents the parsing of some metadata, such as
    the names of the individual images.

    Note
    ----
    The OME schema doesn't provide information about wells at the individual
    *Image* level: see `OME data model <http://www.openmicroscopy.org/Schemas/Documentation/Generated/OME-2015-01/ome.html>`_.
    Instead, it provides a *Plate* element, which contains *Well* elements.
    The *Well* elements contain the positional information, such as row and
    column index of each well within the plate. The *WellSample* elements
    represent individual image acquisition sites within a well and can hold
    metadata, such as the x and y stage positions. In addition, there is an
    *ImageRef* element, which can be used to map a *WellSample* to an
    individual *Image* element.
    The Metamorph software, however, stores all well information in the *.nd*
    file without any direct reference to corresponding *Image* elements.
    Due to the separation of metadata from image files (see above),
    we cannot use the image names (or IDs) as a reference to map the indices
    of the *WellPlateSamples* back to *Image* elements.
    However, the software encodes the well in the filenames. Therefore,
    we can use regular expressions to map image files to wells.
    '''

    @staticmethod
    def _read_nd_file(filename):
        '''
        Read the lines of the *.nd* file as key-value pairs, and format the
        values, i.e. translate them into Python syntax.

        The formatted content will have the following layout
        (shown for a small example dataset)::

            {
                "Description": "File recreated from images.",
                "StartTime1": "20150820 19:43:31.545",
                "DoTimelapse": False,
                "DoStage": True,
                "NStagePositions": 15,
                "Stage1": {'column': 1, 'row': 'A', 'site': 1},
                "Stage2": {'column': 1, 'row': 'A', 'site': 2},
                "Stage3": {'column': 1, 'row': 'A', 'site': 3},
                "Stage4": {'column': 1, 'row': 'A', 'site': 4},
                "Stage5": {'column': 1, 'row': 'A', 'site': 5},
                "Stage6": {'column': 1, 'row': 'A', 'site': 6},
                "Stage7": {'column': 1, 'row': 'A', 'site': 7},
                "Stage8": {'column': 1, 'row': 'A', 'site': 8},
                "Stage9": {'column': 1, 'row': 'A', 'site': 9},
                "Stage10": {'column': 1, 'row': 'A', 'site': 10},
                "Stage11": {'column': 1, 'row': 'A', 'site': 11},
                "Stage12": {'column': 1, 'row': 'A', 'site': 12},
                "Stage13": {'column': 1, 'row': 'A', 'site': 13},
                "Stage14": {'column': 1, 'row': 'A', 'site': 14},
                "Stage15": {'column': 1, 'row': 'A', 'site': 15},
                "DoWave": True,
                "NWavelengths": 2,
                "WaveName1": "sdcGFP",
                "WaveDoZ1": True,
                "WaveName2": "sdcDAPImRFPxm",
                "WaveDoZ2": True,
                "DoZSeries": True,
                "NZSteps": 8,
                "ZStepSize": 1.0,
                "WaveInFileName": True,
            }

        Parameters
        ----------
        filename: str
            absolute path to the *.nd* file

        Returns
        -------
        Dict[str, str or List[str]]
            formatted *.nd* file content
        '''
        with open(filename, 'r') as f:
            content = f.readlines()

        nd = dict()
        for line in content:
            if re.search('NDInfoFile', line) or re.search('EndFile', line):
                continue
            matched = re.search(r'"(.*)", (.+)\r', line)
            key = matched.group(1)
            value = matched.group(2)
            nd[key] = value

        for k, v in nd.iteritems():
            string_match = re.search(r'"(.+)"', v)
            integer_match = re.search(r'^(\d+)$', v)
            if re.search(r'^\d+,\d+$', v):
                v = re.sub(r'^(\d+),(\d+)$', '\\1.\\2', v)
            float_match = re.search(r'^(\d+.\d+)$', v)
            if v == 'TRUE':
                nd[k] = True
            elif v == 'FALSE':
                nd[k] = False
            elif string_match:
                nd[k] = string_match.group(1)
            elif integer_match:
                nd[k] = int(integer_match.group(1))
            elif float_match:
                nd[k] = float(float_match.group(1))

            if re.search(r'^Stage', k):
                row_match = re.search(r'row:(\w+),', v)
                col_match = re.search(r'column:(\d+),', v)
                site_match = re.search(r'site:(\d+)', v)
                if row_match and col_match and site_match:
                    nd[k] = dict()
                    nd[k]['row'] = row_match.group(1)
                    nd[k]['column'] = int(col_match.group(1))
                    nd[k]['site'] = int(site_match.group(1))
        return nd

    def read(self, filename):
        '''
        Read metadata from vendor specific file on disk.

        Parameters
        ----------
        filename: str
            absolute path to the *.nd* file

        Returns
        -------
        bioformats.omexml.OMEXML
            plate metadata
        '''
        metadata = bf.OMEXML()
        # 1) Obtain the general experiment information and well plate format
        #    specifications from the ".nd" file:
        nd = self._read_nd_file(filename)

        # *.stk* files contain a variable number of z-stacks (SizeZ >= 1),
        # but only one time point (SizeT == 1) and one channel (SizeC == 1)
        metadata.image_count = nd['NWavelengths'] * nd['NStagePositions']

        name = os.path.basename(filename)
        plate = metadata.PlatesDucktype(metadata.root_node).newPlate(name=name)
        plate.RowNamingConvention = 'letter'
        plate.ColumnNamingConvention = 'number'
        rows = [nd['Stage%d' % (i+1)]['row']
                for i in xrange(nd['NStagePositions'])]
        plate.Rows = len(set(rows))
        columns = [nd['Stage%d' % (i+1)]['column']
                   for i in xrange(nd['NStagePositions'])]
        plate.Columns = len(set(columns))
        wells = zip(rows, columns)
        for w in set(wells):
            # Create a "Well" instance for each imaged well in the plate
            well = metadata.WellsDucktype(plate).new(row=w[0], column=w[1])
            well_samples = metadata.WellSampleDucktype(well.node)
            # TODO: Is "site" global per plate or local per well?
            well_sample_indices = [nd['Stage%d' % (i+1)]['site']
                                   for i in xrange(nd['NStagePositions'])
                                   if nd['Stage%d' % (i+1)]['row'] == w[0]
                                   and nd['Stage%d' % (i+1)]['column'] == w[1]]
            for s in set(well_sample_indices):
                ix = s-1  # zero-based
                well_samples.new(index=ix)
                # The .nd file doesn't provide any direct reference to the .stk
                # files, we have to solve it via regular expressions (see note)
                well_samples[ix].ImageRef = None

        return metadata
