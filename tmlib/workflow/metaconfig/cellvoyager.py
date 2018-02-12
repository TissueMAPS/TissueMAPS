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
provided in a format specfic to the
`Yokogawa CellVoyager 7000 <http://www.yokogawa.com/solutions/products-platforms/life-science/high-throughput-cytological-discovery-system/cv7000s/>`_
microscope.
'''
import re
import logging
import bioformats
from natsort import natsorted
from collections import defaultdict
from lxml import etree

from tmlib import utils
from tmlib.workflow.illuminati import stitch
from tmlib.workflow.metaconfig.base import MetadataReader
from tmlib.workflow.metaconfig.base import MetadataHandler
from tmlib.workflow.metaconfig.omexml import XML_DECLARATION

logger = logging.getLogger(__name__)

#: Regular expression pattern to identify image files
IMAGE_FILE_REGEX_PATTERN = r'[^_]+_(?P<w>[A-Z]\d{2})_T(?P<t>\d+)F(?P<s>\d+)L\d+A\d+Z(?P<z>\d+)(?P<c>[C]\d{2})\.'

#: Supported extensions for metadata files
METADATA_FILE_REGEX_PATTERN = r'.*\.(mlf|mrf)$'


class CellvoyagerMetadataHandler(MetadataHandler):

    '''Class for handling metadata specific to the Yokogawa Cellvoyager 7000
    microscope.
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
        super(CellvoyagerMetadataHandler, self).__init__(
            omexml_images, omexml_metadata
        )

    @staticmethod
    def _calculate_coordinates(positions, n):
        # y axis is inverted
        return stitch.calc_grid_coordinates_from_positions(
            positions, n, reverse_rows=True
        )

    @classmethod
    def extract_fields_from_filename(cls, regex, filename, defaults=True):
        MetadataFields = super (CellvoyagerMetadataHandler, cls).extract_fields_from_filename(regex, filename, defaults=True)
        
        # Specific for this class
        action = re.search('\dL\d{2}(.+?)Z', filename) # Look for action and change the channel accordingly
        action_number = action.group(1)
        MetadataFields = MetadataFields._replace(c=action_number+"_"+MetadataFields.c)

        return MetadataFields


class CellvoyagerMetadataReader(MetadataReader):

    '''Class for reading metadata from files formats specific to the Yokogawa
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
    '''

    def read(self, microscope_metadata_files, microscope_image_filenames):
        '''Reads metadata from "mlf" and "mrf" metadata files in case they
        are provided.

        Parameters
        ----------
        microscope_metadata_files: List[str]
            absolute path to microscope metadata files
        microscope_image_filenames: List[str]
            names of the corresponding microscope image files

        Returns
        -------
        bioformats.omexml.OMEXML
            OMEXML image metadata

        '''
        microscope_image_filenames = natsorted(microscope_image_filenames)
        metadata = bioformats.OMEXML(XML_DECLARATION)
        if len(microscope_metadata_files) == 0:
            logger.warn('no microscope metadata files found')
            return None
        elif len(microscope_metadata_files) != 2:
            logger.warn('expected two microscope metadata files')
            return None
        for f in microscope_metadata_files:
            if f.endswith('mlf'):
                mlf_filename = f
            elif f.endswith('mrf'):
                mrf_filename = f

        mrf_tree = etree.parse(mrf_filename)
        mrf_root = mrf_tree.getroot()
        mrf_ns = mrf_root.nsmap['bts']

        # Obtain the positional information for each image acquisition site
        # from the ".mlf" file:
        mlf_tree = etree.parse(mlf_filename)
        mlf_root = mlf_tree.getroot()
        record_elements = mlf_root.xpath(
            './/bts:MeasurementRecord', namespaces=mlf_root.nsmap
        )
        mlf_ns = mlf_root.nsmap['bts']

        metadata.image_count = len([
            e for e in record_elements
            if e.attrib['{%s}Type' % mlf_ns] != 'ERR'
        ])
        lookup = defaultdict(list)

        for e in record_elements:
            # Translate positional information into well identifier string
            well_row = utils.map_number_to_letter(
                int(e.attrib['{%s}Row' % mlf_ns]))
            well_col = int(e.attrib['{%s}Column' % mlf_ns])
            well_id = '%s%.2d' % (well_row, well_col)
            if e.attrib['{%s}Type' % mlf_ns] == 'ERR':
                field_index = int(e.attrib['{%s}FieldIndex' % mlf_ns])
                logger.error(
                    'erroneous acquisition - no channel and z-position '
                    'information available at well %s field %d'
                    % (well_id, field_index)
                )
                continue
            # This microscope stores each plane in a separate file. Therefore,
            # we can use the filename to match images.
            name = e.text

            # Check for .tif to .png/.jpg conversion
            if microscope_image_filenames[0].endswith('.png'):
                name = name.replace('.tif','.png')
            elif microscope_image_filenames[0].endswith('.jpg'):
                name = name.replace('.tif','.jpg')


            index = microscope_image_filenames.index(name)
            img = metadata.image(index)
            img.AcquisitionDate = e.attrib['{%s}Time' % mlf_ns]

            # Image files always contain only a single plane
            img.Pixels.SizeT = 1
            img.Pixels.SizeC = 1
            img.Pixels.SizeZ = 1
            img.Pixels.plane_count = 1
            # A name has to be set as a flag for the handler to update
            # the metadata
            img.Name = name
            # Make channel name consistent with how it is encoded in the image
            # file name to ensure that the result is the same, independent of
            # whether it was obtained from the metadata or the image file name.
            img.Pixels.Channel(0).Name = e.attrib['{%s}Ch' % mlf_ns]
            img.Pixels.Plane(0).PositionX = float(e.attrib['{%s}X' % mlf_ns])
            img.Pixels.Plane(0).PositionY = float(e.attrib['{%s}Y' % mlf_ns])
            img.Pixels.Plane(0).PositionZ = float(e.attrib['{%s}Z' % mlf_ns])
            img.Pixels.Plane(0).TheZ = int(e.attrib['{%s}ZIndex' % mlf_ns])
            img.Pixels.Plane(0).TheT = int(e.attrib['{%s}TimelineIndex' % mlf_ns])

            idx = microscope_image_filenames.index(img.Name)
            lookup[well_id].append(idx)

        # Obtain the general experiment information and well plate format
        # specifications from the ".mrf" file:
        name = mrf_root.attrib['{%s}Title' % mrf_ns]
        plate = metadata.PlatesDucktype(metadata.root_node).newPlate(name=name)
        plate.RowNamingConvention = 'letter'
        plate.ColumnNamingConvention = 'number'
        plate.Rows = mrf_root.attrib['{%s}RowCount' % mrf_ns]
        plate.Columns = mrf_root.attrib['{%s}ColumnCount' % mrf_ns]
        wells = lookup.keys()
        for w in set(wells):
            # Create a *Well* element for each imaged well in the plate
            row = utils.map_letter_to_number(w[0]) - 1
            col = int(w[1:]) - 1
            well = metadata.WellsDucktype(plate).new(row=row, column=col)
            well_samples = metadata.WellSampleDucktype(well.node)
            for i, ref in enumerate(lookup[w]):
                # Create a *WellSample* element for each acquisition site
                well_samples.new(index=i)
                well_samples[i].ImageRef = ref

        return metadata
