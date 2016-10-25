'''Implementation of classes for reading microscope image and metadata files
provided in a format specific to microscopes equipped
with
`Nikon NISElements <https://www.nikoninstruments.com/Products/Software>`_
software.
'''

import os
import re
import logging
import bioformats
import numpy as np
from collections import defaultdict

from tmlib import utils
from tmlib.workflow.illuminati import stitch
from tmlib.workflow.metaconfig.base import MetadataReader
from tmlib.workflow.metaconfig.base import MetadataHandler
from tmlib.workflow.metaconfig.omexml import XML_DECLARATION

logger = logging.getLogger(__name__)

#: Regular expression pattern to identify image files
IMAGE_FILE_REGEX_PATTERN = '.+\.nd2'

#: Supported extensions for metadata files
METADATA_FILE_REGEX_PATTERN = r'.+\.txt'


class NiselementsMetadataHandler(MetadataHandler):

    '''Class for handling metadata specific to microscopes equipped with
    NISElements software.
    '''

    #: Regular expression pattern to identify image files
    IMAGE_FILE_REGEX_PATTERN = IMAGE_FILE_REGEX_PATTERN

    def __init__(self, omexml_images, omexml_metadata=None):
        '''
        Parameters
        ----------
        omexml_images: Dict[str, bioformats.omexml.OMEXML]
            metadata extracted from microscope image files
        omexml_metadata: bioformats.omexml.OMEXML
            metadata extracted from microscope metadata files
        '''
        super(NiselementsMetadataHandler, self).__init__(
            omexml_images, omexml_metadata
        )

    @staticmethod
    def _calculate_coordinates(positions, n):
        # x axis is inverted
        return stitch.calc_grid_coordinates_from_positions(
            positions, n, reverse_columns=True
        )


class NiselementsMetadataReader(MetadataReader):

    '''Class for reading metadata from files formats specific to microscopes
    equipped with NISElements software.

    '''

    def read(self, microscope_metadata_files, microscope_image_files):
        '''Read metadata from "txt" metadata file.

        Parameters
        ----------
        microscope_metadata_files: List[str]
            absolute path to the microscope metadata files
        microscope_image_files: List[str]
            absolute path to the microscope image files

        Returns
        -------
        bioformats.omexml.OMEXML
            OMEXML image metadata
        '''
        metadata = bioformats.OMEXML(XML_DECLARATION)
        if len(microscope_metadata_files) != 1:
            raise ValueError('Expected one microscope metadata file.')
        txt_filename = microscope_metadata_files[0]
        if not re.search(METADATA_FILE_REGEX_PATTERN, txt_filename):
            raise ValueError('Microscope metadata file has wrong format.')

        with open(txt_filename, 'rU') as f:
            content = f.read()
        content = content.decode('utf-16-le').replace('\t', ' ').splitlines()

        strip = False
        count = 0
        lookup = defaultdict(list)
        positions = list()
        for line in content:
            line = line.decode()
            if 'Spectral Loop' in line:
                strip = False
            if strip:
                if line:
                    well_position, x, y, _ = tuple(line.split(' '))
                    well_name, field_index = tuple(well_position.split('_'))
                    field_index = int(field_index)
                    row = utils.map_letter_to_number(well_name[0])
                    column = int(well_name[1:])
                    positions.append((x, y))
                    lookup[(row, column)].append(count)
                    count += 1
            if 'Point Name' in line:
                strip = True

        # Get number of planes and use this info somehow to build a reference
        metadata.image_count = count
        for i in xrange(count):
            img = metadata.image(i)
            img.Name = None
            img.Pixels.SizeT = 1
            img.Pixels.SizeC = 1
            img.Pixels.SizeZ = 1
            img.Pixels.plane_count = 1
            x, y = positions[i]
            img.Pixels.Plane(0).PositionX = x
            img.Pixels.Plane(0).PositionY = y

        name = os.path.splitext(os.path.basename(microscope_image_files[0]))[0]
        plate = metadata.PlatesDucktype(metadata.root_node).newPlate(name=name)
        plate.RowNamingConvention = 'letter'
        plate.ColumnNamingConvention = 'number'
        well_coordinates = np.array(lookup.keys())
        if any(well_coordinates[:, 0] > 8) or any(well_coordinates[:, 1] > 12):
            # 384 well plate
            plate.Rows = 16
            plate.Columns = 24
        else:
            # 96 well plate
            plate.Rows = 8
            plate.Columns = 12
        for row, col in lookup.keys():
            # Create a *Well* element for each imaged well in the plate
            well = metadata.WellsDucktype(plate).new(row=row-1, column=col-1)
            well_samples = metadata.WellSampleDucktype(well.node)
            for index, reference in enumerate(lookup[(row, col)]):
                # Create a *WellSample* element for each acquisition site
                well_samples.new(index=index)
                well_samples[index].ImageRef = reference
        return metadata


