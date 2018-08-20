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
'''Workflow step for creation of pyramid images.

To achieve efficient zoomable visualization of terabyte-size microscopy image
dataasets accross multiple resolution levels, images need to be represented in
`pyramid <https://en.wikipedia.org/wiki/Pyramid_(image_processing)>` _ format.
To this end, the `illuminati` step casts images to 8-bit and tiles them up
according to available positional information.
Users further have the option to correct images for illumination artifacts and
align them between acquisitions based on pre-calculated statistics (if
available).

'''
from tmlib import __version__


__dependencies__ = {'imextract'}

__optional_dependencies__ = {'align', 'corilla'}

__fullname__ = 'Pyramid image builder'

__description__ = (
    'Creation of pyramids for interactive, web-based visualization of images.'
)

__logo__ = u'''
   .
   I        {name} ({version})
  LLU       {fullname}
 MINATI     https://github.com/TissueMAPS/TmLibrary
'''.format(name=__name__, version=__version__, fullname=__fullname__)
