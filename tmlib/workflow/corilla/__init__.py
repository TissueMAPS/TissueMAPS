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
'''Workflow step for correction of illumination artifacts.

Microscopic images generally display inhomogeneous illumination. Correction of
these artifacts is important for visualization and even more so for
quantitative analysis of pixel intensities. To this end, the `corilla` step
calculated illumination statistics across all acquisition sites. These
statistics are stored and can later be applied to individual images to correct
them for illumination artifacts. The step further computes global intensity
statistics, which can be useful to uniformly rescale intensities across images.

'''
from tmlib import __version__

__dependencies__ = {'imextract'}

__fullname__ = 'Correction of illumination artifacts'

__description__ = (
    'Calculation of illumination statistics over a set of '
    'images belonging to the same channel. The resulting statistics can '
    'subsequently be applied to individual images to correct them for '
    'illumination artifacts.'
)

__logo__ = u'''
             _ _ _
  __ ___ _ _(_) | |__ _     {name} ({version})
 / _/ _ \ '_| | | / _` |    {fullname}
 \__\___/_| |_|_|_\__,_|    https://github.com/TissueMAPS/TmLibrary
'''.format(name=__name__, version=__version__, fullname=__fullname__)
