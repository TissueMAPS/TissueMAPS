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
import os
import logging

from tmlib import cfg


logger = logging.getLogger(__name__)


def determine_language(filename):
    '''Determines language of a module from filename suffix.

    Parameters
    ----------
    filename: str
        name of a module file

    Returns
    -------
    str
    '''
    suffix = os.path.splitext(filename)[1]
    if suffix == '.m':
        return 'Matlab'
    elif suffix == '.R' or suffix == '.r':
        return 'R'
    elif suffix == '.py':
        return 'Python'
    else:
        raise Exception('Language could not be determined from filename.')
