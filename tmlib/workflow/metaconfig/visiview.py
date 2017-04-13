# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''Implementation of classes for reading microscope image and metadata files
provided in a format specific to microscopes equipped
with
`Visitron VisiView <http://www.visitron.de/Products/Software/VisiView/visiview.html>`_
software.
'''

import os
import re
import logging
import bioformats
from natsort import natsorted
from collections import defaultdict

from tmlib import utils
from tmlib.workflow.metaconfig.base import MetadataReader
from tmlib.workflow.metaconfig.base import MetadataHandler
from tmlib.workflow.metaconfig.omexml import XML_DECLARATION

logger = logging.getLogger(__name__)

#: Regular expression pattern to identify image files
IMAGE_FILE_REGEX_PATTERN = '.+_?(?P<w>[A-Z]\d{2})?_w\d+(?P<c>\w+)_s(?P<s>\d+)_?t?(?P<t>\d+)?\.'

#: Supported extensions for metadata files
METADATA_FILE_REGEX_PATTERN = '\.nd$'


class VisiviewMetadataHandler(MetadataHandler):

    '''Class for handling metadata specific to microscopes equipped with
    Visitron software.

    Warning
    -------
    The *.stk* file format is in principle supported by BioFormats.
    However, if the *.nd* file is provided in the same folder, then the
    metadata of all files are read for each individual *.stk* file.
    To prevent this, the *.nd* file has to be separated from the *.stk* files,
    i.e. placed in another folder.
    '''

    def __init__(self, omexml_images, omexml_metadata=None):
        '''
        Parameters
        ----------
        omexml_images: Dict[str, bioformats.omexml.OMEXML]
            metadata extracted from microscope image files
        omexml_metadata: bioformats.omexml.OMEXML
            metadata extracted from microscope metadata files 
        '''
        super(VisiviewMetadataHandler, self).__init__(
            omexml_images, omexml_metadata
        )


def read_nd_file(filename):
    '''Read the lines of the *.nd* file as key-value pairs, and format the
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


class VisiviewMetadataReader(MetadataReader):

    '''Class for reading metadata from files formats specific to microscopes
    equipped with the VisiView software.

    Note
    ----
    These formats are generally supported by Bio-Formats. However, by default
    Bio-Formats reads metadata for all files simultaneously using both the
    *.nd* as well as the "*.stk" files. This breaks the logic of individual
    file reading and can only be prevented by separating the *.nd* file from
    the *.stk* files, i.e. placing them into separate folders.
    However, this in turn prevents the parsing of some metadata, such as
    the names of the individual images.

    The VisiView software stores all well information in the *.nd* file, but
    without any direct reference to corresponding *Image* elements.
    Due to the separation of metadata from image files (see above),
    we cannot use the image names (or IDs) as a reference to map the indices
    of the *WellPlateSamples* back to *Image* elements.
    However, the software encodes the well id in the filenames. Therefore,
    we can use regular expressions to map image files to wells.
    '''

    def read(self, microscope_metadata_files, microscope_image_filenames):
        '''Read metadata from "nd" metadata file.

        Parameters
        ----------
        microscope_metadata_files: List[str]
            absolute path to the microscope metadata files
        microscope_image_filenames: List[str]
            names of the corresponding microscope image files

        Returns
        -------
        bioformats.omexml.OMEXML
            OMEXML image metadata

        Raises
        ------
        ValueError
            when `microscope_metadata_files` doesn't have length one
        '''
        microscope_image_filenames = natsorted(microscope_image_filenames)
        if len(microscope_metadata_files) != 1:
            raise ValueError('Expected one microscope metadata file.')
        nd_filename = microscope_metadata_files[0]
        metadata = bioformats.OMEXML(XML_DECLARATION)
        # 1) Obtain the general experiment information and well plate format
        #    specifications from the ".nd" file:
        nd = read_nd_file(nd_filename)

        metadata.image_count = nd['NStagePositions']
        if nd['DoWave']:
            metadata.image_count *= nd['NWavelengths']
        if nd['DoTimelapse']:
            metadata.image_count *= nd['NTimePoints']

        for i in xrange(metadata.image_count):
            img = metadata.image(i)
            img.Name = ''
            # Images files may contain a variable number of z-stacks
            # (SizeZ >= 1), but only one time point (SizeT == 1)
            # and one channel (SizeC == 1)
            img.Pixels.SizeT = 1
            img.Pixels.SizeC = 1
            img.Pixels.SizeZ = nd['NZSteps']
            img.Pixels.plane_count = nd['NZSteps']

        # TODO: case when no stage positions are available (manual acquisition)

        name = os.path.splitext(os.path.basename(nd_filename))[0]
        plate = metadata.PlatesDucktype(metadata.root_node).newPlate(name=name)
        plate.RowNamingConvention = 'letter'
        plate.ColumnNamingConvention = 'number'
        rows = [
            nd['Stage%d' % (i+1)]['row']
            for i in xrange(nd['NStagePositions'])
        ]
        plate.Rows = len(set(rows))
        columns = [
            nd['Stage%d' % (i+1)]['column']
            for i in xrange(nd['NStagePositions'])
        ]
        plate.Columns = len(set(columns))

        # Create a lut table to get all images planes per well
        sites = [
            nd['Stage%d' % (i+1)]['site']
            for i in xrange(nd['NStagePositions'])
        ]
        wells = [
            '%s%.2d' % (rows[i], columns[i])
            for i in xrange(len(sites))
        ]
        lut = defaultdict(list)
        for i, filename in enumerate(natsorted(microscope_image_filenames)):
            fields = MetadataHandler.extract_fields_from_filename(
                IMAGE_FILE_REGEX_PATTERN, filename, defaults=False
            )
            # NOTE: We assume that the "site" id is global per plate
            field_index = sites.index(int(fields.s))
            lut[wells[field_index]].append(i)

        for w in set(wells):
            # Create a "Well" instance for each imaged well in the plate
            row_index = utils.map_letter_to_number(w[0]) - 1
            col_index = int(w[1:]) - 1
            well = metadata.WellsDucktype(plate).new(
                row=row_index, column=col_index
            )
            well_samples = metadata.WellSampleDucktype(well.node)
            for i, ref in enumerate(lut[w]):
                # Create a *WellSample* element for each acquisition site
                well_samples.new(index=i)
                well_samples[i].ImageRef = ref

        return metadata
