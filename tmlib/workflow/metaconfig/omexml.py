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
import re
from tmlib.errors import RegexError


def get_image_ix(image_id):
    '''
    Get the index of an image within the OMEXML metadata object given the
    ID of the image.

    Parameters
    ----------
    image_id: str
        image identifier in the format ``Image:\d+``

    Returns
    -------
    int
        zero-based index number
    '''
    match = re.search(r'^Image:(\d+)$', image_id)
    if not match:
        RegexError('Index of image could not be determined from image ID.')
    return int(match.group(1))


'''OMEXML declaration configuration.
For details see `OME model <http://www.openmicroscopy.org/site/support/ome-model/>`_
'''

OME_VERSION = '2015-01'

XML_FIELDNAMES = {
    'schema_name': 'http://www.openmicroscopy.org/Schemas/OME/{version}',
    'schema_inst': 'http://www.w3.org/2001/XMLSchema-instance',
    'schema_loc': 'http://www.openmicroscopy.org/Schemas/OME/{version} http://www.openmicroscopy.org/Schemas/OME/{version}/ome.xsd',
    'sa': 'http://www.openmicroscopy.org/Schemas/SA/{version}',
    'spw': 'http://www.openmicroscopy.org/Schemas/SPW/{version}'
}

XML_DECLARATION = '''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<OME xmlns="{schema_name}" xmlns:xsi="{schema_inst}" xsi:schemaLocation="{schema_loc}">
    <StructuredAnnotations xmlns="{sa}">
    </StructuredAnnotations>
    <SPW xmlns="{spw}">
    </SPW>
</OME>
'''.format(**XML_FIELDNAMES).format(version=OME_VERSION)
