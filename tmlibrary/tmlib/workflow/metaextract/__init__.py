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
'''Workflow step for extraction of microscope image metadata.

Microscopes typically write metadata about the image acquisition process into
the header of the generated image files. Unfortunately, almost every vendor
uses a custom file format. The `metaextract` step uses the
`Bio-Formats <https://www.openmicroscopy.org/site/products/bio-formats>`_
library to extract metadata from heterogeneous image file formats in form of
`OMEXML <https://www.openmicroscopy.org/site/support/ome-model/ome-xml/index.html>`_
according to the standardized
`OME <https://www.openmicroscopy.org/site/support/ome-model/>`_ data model.

'''
from tmlib import __version__

__dependencies__ = {}

__fullname__ = 'Extraction of image metadata'

__description__ = (
    'Extraction of OMEXML metadata from heterogeneous microscopy image '
    'file formats.'
)

__logo__ = '''
            _                _               _
  _ __  ___| |_ __ _ _____ _| |_ _ _ __ _ __| |_    {name} ({version})
 | '  \/ -_)  _/ _` / -_) \ /  _| '_/ _` / _|  _|   {fullname}
 |_|_|_\___|\__\__,_\___/_\_\\\__|_| \__,_\__|\__|   https://github.com/TissueMAPS/TmLibrary
'''.format(name=__name__, version=__version__, fullname=__fullname__)



