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
'''Data analysis tools.

'''
import os
import logging
import importlib
from tmlib.tools.classification import Classification
from tmlib.tools.clustering import Clustering
from tmlib.tools.heatmap import Heatmap

from tmlib.tools.version import __version__

logger = logging.getLogger(__name__)


SUPPORTED_TOOLS = {'Clustering', 'Classification', 'Heatmap'}


def get_tool_class(name):
    '''Gets the tool-specific implementation of :class:`tmlib.models.tool.Tool`.

    Parameters
    ----------
    name: str
        name of the tool

    Returns
    -------
    type
        tool class
    '''
    tool_module = import_tool_module(name)
    logger.debug('get class for tool "%s"', name)
    return getattr(tool_module, name)


def import_tool_module(name):
    '''Imports the module for an implemented `tool`.

    Parameters
    ----------
    name: str
        name of the tool

    Returns
    -------
    module
        loaded module instance

    Raises
    ------
    ValueError
        when no tool is know for the given `name` or when no respective module
        is found
    '''
    if name not in SUPPORTED_TOOLS:
        raise ValueError(
            'Unknown tool "%s".\n'
            'Supported are: "%s"' % '", "'.join(SUPPORTED_TOOLS)
        )
    name = name.lower()
    tool_module_filename = '%s.py' % name
    module_files = [
        f for f in os.listdir(os.path.dirname(__file__))
        if f != '__init__.py'
    ]
    if tool_module_filename not in module_files:
        raise ValueError('No module found for tool "%s"', name)
    module_path = '%s.%s' % (__name__, name)
    return importlib.import_module(module_path)

