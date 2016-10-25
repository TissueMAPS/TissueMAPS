'''Implementation of classes for reading microscope image and metadata files
provided in a format specific to microscopes equipped
with
`GE InCell <http://www.gelifesciences.com/webapp/wcs/stores/servlet/catalog/en/GELifeSciences/brands/in-cell-analyzer/>`_
software.
'''

import os
import re
import logging
import bioformats
from collections import defaultdict
from lxml import etree

from tmlib import utils
from tmlib.workflow.metaconfig.base import MetadataReader
from tmlib.workflow.metaconfig.base import MetadataHandler
from tmlib.workflow.metaconfig.omexml import XML_DECLARATION

logger = logging.getLogger(__name__)

#: Regular expression pattern to identify image files
#: Who names files like this this???
IMAGE_FILE_REGEX_PATTERN = r'[A-Z][\s_]-[\s_]\d+\(*[a-z]+[\s_]\d+[\s_][a-z]+[\s_]\w+[\s_]-[\s_]\w+\)*\.tif'

#: Supported extensions for metadata files
METADATA_FILE_REGEX_PATTERN = r'.+\.xdce'


class IncellMetadataHandler(MetadataHandler):

    '''Class for handling metadata specific to microscopes equipped with
    InCell software.
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
        super(IncellMetadataHandler, self).__init__(
            omexml_images, omexml_metadata
        )

    # @staticmethod
    # def _calculate_coordinates(positions, n):
    #     # TODO: coordinates are not absolute, but relative to well center.
    #     # This requires a different approach.

class IncellMetadataReader(MetadataReader):

    '''Class for reading metadata from files formats specific to microscopes
    equipped with InCell software.

    '''

    def read(self, microscope_metadata_files, microscope_image_files):
        '''Read metadata from "xdce" metadata file.

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
        xdce_filename = microscope_metadata_files[0]
        if not re.search(METADATA_FILE_REGEX_PATTERN, xdce_filename):
            raise ValueError('Microscope metadata file has wrong format.')
        tree = etree.parse(xdce_filename)
        root = tree.getroot()
        lookup = defaultdict(list)
        image_elements = root.xpath('//ImageStack/Images/Image')
        metadata.image_count = len(image_elements)
        for count, e in enumerate(image_elements):
            img = metadata.image(count)
            # time is provided in milliseconds and not as datetime
            img.AcquisitionDate = e.attrib['acquisition_time_ms']
            # Each plane seems to be stored in separate "Image" element
            img.Pixels.SizeT = 1
            img.Pixels.SizeC = 1
            img.Pixels.SizeZ = 1
            img.Pixels.plane_count = 1
            img_name = e.attrib['filename']
            img_name = img_name.replace(' ', '_')
            img_name = img_name.replace('(', '')
            img_name = img_name.replace(')', '')
            img.Name = img_name
            channel_name = e.find('.//EmissionFilter').attrib['name']
            img.Pixels.Channel(0).Name = channel_name
            xy_pos_element = e.find('.//OffsetFromWellCenter')
            z_pos_element = e.find('.//FocusPosition')
            img.Pixels.Plane(0).PositionX = float(xy_pos_element.attrib['x'])
            img.Pixels.Plane(0).PositionY = float(xy_pos_element.attrib['y'])
            img.Pixels.Plane(0).PositionZ = float(z_pos_element.attrib['z'])
            identifier_element = e.find('.//Identifier')
            img.Pixels.Plane(0).TheC = int(identifier_element.attrib['wave_index'])
            img.Pixels.Plane(0).TheT = int(identifier_element.attrib['time_index'])
            img.Pixels.Plane(0).TheZ = int(identifier_element.attrib['z_index'])
            field_index = int(identifier_element.attrib['field_index'])
            well_row = int(e.find('.//Well/Row').attrib['number'])
            well_column = int(e.find('.//Well/Column').attrib['number'])
            lookup[(well_row, well_column)].append(img.Name)

        plate_element = root.find('.//AutoLeadAcquisitionProtocol/Plate')
        name = plate_element.attrib['name']
        plate = metadata.PlatesDucktype(metadata.root_node).newPlate(name=name)
        plate.RowNamingConvention = 'letter'
        plate.ColumnNamingConvention = 'number'
        plate.Rows = int(plate_element.attrib['rows'])
        plate.Columns = int(plate_element.attrib['columns'])
        for row, col in lookup.keys():
            # Create a *Well* element for each imaged well in the plate
            well = metadata.WellsDucktype(plate).new(row=row-1, column=col-1)
            well_samples = metadata.WellSampleDucktype(well.node)
            for index, reference in enumerate(lookup[(row, col)]):
                # Create a *WellSample* element for each acquisition site
                well_samples.new(index=index)
                well_samples[index].ImageRef = reference

        return metadata
