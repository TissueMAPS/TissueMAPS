import os
import importlib
from classification import Classification
from clustering import Clustering
from heatmap import Heatmap


SUPPORTED_TOOLS = {'Clustering', 'Classification', 'Heatmap'}


def get_tool_class(name):
    '''Gets the tool-specific implementation of :py:class:`tmserver.tool.Tool`.

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

