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
'''Workflow step for registration and alignment of microscopy images.

When images are acquired at the different time points they may exhibit a
displacement relative to each other. To overlay these image for visualization
or analysis, they need to be registered and aligned between acquisitions.
To this end, the `align` step computes translational shifts of each image
acquired at the same site relative to one reference image (by default the
one of the first acquisition time point). The computed shift values are stored
and can later be applied for alignment.
Note that translations are computed only per site and no attempt is made to
find a globally optimal alignment. This is done for performance reasons and
to simplify parallelization.
'''
from tmlib import __version__

__dependencies__ = {'imextract'}

__fullname__ = 'Align images between acquisitions'

__description__ = (
    'Registration of images acquired in different multiplexing '
    'cycles relative to a reference cycle. The calculated shifts can then '
    'subsequently be used to align images.'
)

__logo__ = u'''
       _ _
  __ _| (_)__ _ _ _         {name} ({version})
 / _` | | / _` | ' \        {fullname}
 \__,_|_|_\__, |_||_|       https://github.com/TissueMAPS/TmLibrary
          |___/
'''.format(name=__name__, version=__version__, fullname=__fullname__)
