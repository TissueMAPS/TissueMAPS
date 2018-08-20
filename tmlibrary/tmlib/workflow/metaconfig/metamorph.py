# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016-2018 University of Zurich.
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
`Metamorph <https://www.moleculardevices.com/systems/metamorph-research-imaging/metamorph-microscopy-automation-and-image-analysis-software>`_
software.
'''

import os
import re
import logging
import bioformats
from collections import defaultdict

from tmlib import utils
from tmlib.workflow.metaconfig.base import MetadataReader
from tmlib.workflow.metaconfig.base import MetadataHandler
from tmlib.workflow.metaconfig.omexml import XML_DECLARATION

logger = logging.getLogger(__name__)

#: Regular expression pattern to identify image files
# TODO: how are time points encoded?

IMAGE_FILE_REGEX_PATTERN = '.+_?(?P<w>[A-Z]\d{2})_s(?P<s>\d+)(_w(?P<c>\d{1}))?[^_thumb]'

#: Supported extensions for metadata files
METADATA_FILE_REGEX_PATTERN = r'(?!.*)'


class MetamorphMetadataHandler(MetadataHandler):

    '''Class for handling metadata specific to microscopes equipped with
    Metamorph software.
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
        super(MetamorphMetadataHandler, self).__init__(
            omexml_images, omexml_metadata
        )
