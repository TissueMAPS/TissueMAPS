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
import logging

from tmlib import cfg


logger = logging.getLogger(__name__)


def get_package_directories():
    '''Gets the language-specific package directories were module source
    files are located.

    Returns
    -------
    Dict[str, str]
        paths to module directories for each language relative to the
        repository directory
    '''
    dirs = {
        'Python': 'src/python/jtmodules',
        'Matlab': 'src/matlab/+jtmodules',
        'R': 'src/r/jtmodules'
    }
    return {k: os.path.join(cfg.modules_home, v) for k, v in dirs.iteritems()}


def get_module_path(module_file):
    '''Gets the absolute path to a module file.

    Parameters
    ----------
    module_file: str
        name of the module file
    repo_dir: str
        absolute path to the local copy of the `jtlib` repository

    Returns
    -------
    str
        absolute path to module file
    '''
    language = determine_language(module_file)
    modules_dir = get_package_directories()[language]
    return os.path.join(modules_dir, module_file)


def determine_language(filename):
    '''Determines language form module filename suffix.

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
