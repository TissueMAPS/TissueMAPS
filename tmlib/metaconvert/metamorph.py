import os
import re
import bioformats
from .default import MetadataHandler
from ..readers import MetadataReader
from ..plates import WellPlate


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
        metadata = bioformats.OMEXML()
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
        sites = [nd['Stage%d' % (i+1)]['site']
                 for i in xrange(nd['NStagePositions'])]
        wells = zip(rows, columns, sites)
        for w in set(wells):
            # Create a "Well" instance for each imaged well in the plate
            row_index = WellPlate.name_to_index(w[0])
            col_index = w[1]
            well = metadata.WellsDucktype(plate).new(row=row_index,
                                                     column=col_index)
            well_samples = metadata.WellSampleDucktype(well.node)
            well_sample_indices = [nd['Stage%d' % (i+1)]['site']
                                   for i in xrange(nd['NStagePositions'])
                                   if nd['Stage%d' % (i+1)]['row'] == w[0]
                                   and nd['Stage%d' % (i+1)]['column'] == w[1]]
            for s in set(well_sample_indices):
                # TODO: Is "site" global per plate or local per well?
                file_indices = [i for i in xrange(nd['NStagePositions'])
                                if nd['Stage%d' % (i+1)]['site'] == s]
                ix = s-1  # zero-based
                well_samples.new(index=ix)
                # The .nd file doesn't provide any direct reference to the .stk
                # files, we have to solve it via regular expressions (see note)
                sites = [str(i+1) for i in file_indices]
                well_samples[ix].ImageRef = {r'_s(\d+)\.stk$': sites}

        return metadata


class MetamorphMetadataHandler(MetadataHandler):

    '''
    Class for reading metadata files specific to microscopes equipped with
    Metamorph or Visitron software.

    Warning
    -------
    The *.stk* file format is in principle supported by Bio-Formats.
    However, if the *.nd* file is provided in the same folder, then the
    metadata of all files are read for each individual *.stk* file.
    To prevent this, the *.nd* file has to be separated from the *.stk* files,
    i.e. placed in another folder.
    '''

    formats = {'.nd'}

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
        super(MetamorphMetadataHandler, self).__init__(
                image_files, additional_files, ome_xml_files, cycle_name)
        self.image_files = image_files
        self.additional_files = additional_files
        self.ome_xml_files = ome_xml_files
        self.cycle_name = cycle_name

    @property
    def updated_additional_files(self):
        files = [f for f in self.additional_files
                 if os.path.splitext(f)[1] in self.formats]
        if (len(files) > len(self.formats) or len(files) == 0
                or (len(files) < len(self.formats) and len(files) > 0)):
            raise OSError('%d metadata files are required: "%s"'
                          % (len(self.formats), '", "'.join(self.formats)))
        else:
            self._additional_files = dict()
            for mdf in self.formats:
                self._additional_files[mdf] = [f for f in files
                                               if f.endswith(mdf)]
        return self._additional_files

    @property
    def ome_additional_metadata(self):
        '''
        Returns
        -------
        bioformats.omexml.OMEXML
            metadata retrieved from Visitron microscope-specific files

        See also
        --------
        `MetamorphMetadataReader`_
        '''
        with MetamorphMetadataReader() as reader:
            nd_path = self.updated_additional_files['.nd'][0]
            self._ome_additional_metadata = reader.read(nd_path)
        return self._ome_additional_metadata
