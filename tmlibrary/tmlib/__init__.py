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
'''`TissueMAPS` library.

The package provides active programming and command line interfaces for
distributed image analysis.

It has three subpackages that serve different tasks:

    * :mod:`tmlib.models`: object-relational mapper classes for interaction
      with the database
    * :mod:`tmlib.workflow`: modular routines for distributed image processing
    * :mod:`tmlib.tools`: plugins for interactive machine learning

'''
import os
import glob
from pkg_resources import resource_filename

from tmlib.version import __version__
from tmlib.config import LibraryConfig

cfg = LibraryConfig()
