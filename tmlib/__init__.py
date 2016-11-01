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
import os
import glob
from pkg_resources import resource_filename

from tmlib.version import __version__
from tmlib.config import LibraryConfig

cfg = LibraryConfig()


def get_cli_tools():
    '''Lists command line interfaces for implemented steps.

    Returns
    -------
    List[str]
        names of cli tools
    '''
    root = resource_filename(__name__, 'workflow')
    def _is_package(d):
        # A step is defined as a subpackage that implements the following
        # modules: api, cli, args
        d = os.path.join(root, d)
        return(
            os.path.isdir(d) and
            glob.glob(os.path.join(d, '__init__.py')) and
            glob.glob(os.path.join(d, 'api.py')) and
            glob.glob(os.path.join(d, 'cli.py')) and
            glob.glob(os.path.join(d, 'args.py'))
        )

    return filter(_is_package, os.listdir(root))

