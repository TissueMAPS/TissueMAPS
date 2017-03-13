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
'''Workflow step for building and running image analysis pipelines.

The objective of image analysis is to identify meaningful objects (e.g. "cells")
in the images and extract features for the identified objects.
The `jterator` step provides users an interface to combine individual modules
available via the `JtModules repository <https://github.com/TissueMAPS/JtModules>`_
into custom image analysis *pipelines* in a
`CellProfiler <http://cellprofiler.org/>`_-like manner.
Outlines of segmented objects and extracted feature values can be stored for
further analyis or interactive visualization in the viewer.

'''
from tmlib import __version__

__dependencies__ = {'imextract'}

__optional_dependencies__ = {'align', 'corilla'}

__fullname__ = 'Image analysis pipeline engine'

__description__ = (
    'Application of a sequence of algorithms to a set of images '
    'to segment the images and extract features for the identified objects.'
)

__logo__ = '''
    _ _                _
   (_) |_ ___ _ _ __ _| |_ ___ _ _      {name} ({version})
   | |  _/ -_) '_/ _` |  _/ _ \ '_|     {fullname}
  _/ |\__\___|_| \__,_|\__\___/_|       https://github.com/TissueMAPS/TmLibrary
 |__/
'''.format(name=__name__, version=__version__, fullname=__fullname__)
