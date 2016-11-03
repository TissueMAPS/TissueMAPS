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
import inspect
import logging
import importlib
from tmlib.errors import RegistryError

logger = logging.getLogger(__name__)

_tool_register = dict()


def register_tool(cls):
    '''Class decorator to register a derived class of
    :class:`tmlib.tools.base.Tool` and make it available for use in the UI.

    Parameters
    ----------
    cls: type
        tool class that should be registered

    Returns
    -------
    cls
        registered tool class

    Raises
    ------
    TypeError
        when decorated class is not derived from
        :class:`tmlib.tools.base.Tool`
    '''
    from tmlib.tools.base import Tool
    if Tool not in inspect.getmro(cls):
        raise TypeError(
            'Tool class must be derived from "tmlib.tools.base.Tool"'
        )
    _tool_register[cls.__name__] = cls
    return cls


def get_tool_class(name):
    '''Gets the tool-specific implementation of :class:`tmlib.models.base.Tool`.

    Parameters
    ----------
    name: str
        name of the tool

    Returns
    -------
    type
        tool class
    '''
    # module_name = '%s.%s' % (__name__, name.lower())
    # try:
    #     module = importlib.import_module(module_name)
    # except ImportError as error:
    #     raise ImportError(
    #         'Import of module "%s" failed: %s' % (module_name, str(error))
    #     )
    try:
        return _tool_register[name]
    except KeyError:
        raise RegistryError('Tool "%s" is not registered.' % name)


def get_available_tools():
    '''Gets a list of available tools.

    Returns
    -------
    List[str]
        names of available tools
    '''
    return _tool_register.keys()
