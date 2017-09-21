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
'''Workflow step for configuration of microscopy image metadata.

Metadata available from the microscope image files is often incomplete, either
because the format is not fully supported by the `Bio-Formats` library or
simply because the microscope provides insufficient information in the files.
In particular, the relative position of images, required for overview creation,
is typically not available from individual image files. The `metaconfig` step
configures metadata extracted from image files in the
:mod:`tmlib.workflow.metaextract` step and tries to obtain any missing
information from microscope-specific metadata files or user input.

This is achieved via microscope-specific implementations of
:class:`MetadataReader <tmlib.workflow.metaconfig.base.MetadataReader>` and
:class:`MetadataHandler <tmlib.workflow.metaconfig.base.MetadataHandler>` in
a separate module of :mod:`tmlib.workflow.metaconfig`.
The name given to the module determines the microscope type, e.g.
:mod:`tmlib.workflow.metaconfig.cellvoyager` is the module for the
``cellvoyager`` microscope type.

To make the micorscope type available for usage add its name (name of the
implemented module) to
:const:`SUPPORTED_MICROSCOPE_TYPES <tmlib.workflow.metaconfig.SUPPORTED_MICROSCOPE_TYPES>`.
'''
import re
import importlib
import inspect
import logging

from tmlib import __version__
from tmlib.workflow.metaconfig.base import MetadataReader
from tmlib.workflow.metaconfig.base import MetadataHandler

logger = logging.getLogger(__name__)

__dependencies__ = {'metaextract'}

__fullname__ = 'Configuration of image metadata'

__description__ = (
    'Configuration of extracted OMEXML metadata '
    'and integration with additional microscope-specific information about '
    'the image acquisition process.'
)

__logo__ = '''
            _                     __ _
  _ __  ___| |_ __ _ __ ___ _ _  / _(_)__ _         {name} ({version})
 | '  \/ -_)  _/ _` / _/ _ \ ' \|  _| / _` |        {fullname}
 |_|_|_\___|\__\__,_\__\___/_||_|_| |_\__, |        https://github.com/TissueMAPS/TmLibrary
                                      |___/
'''.format(name=__name__, version=__version__, fullname=__fullname__)


SUPPORTED_MICROSCOPE_TYPES = {
    'visiview', 'cellvoyager', 'metamorph'
}


def import_microscope_type_module(microscope_type):
    '''Imports the module for an implemented `microscope_type`.

    Parameters
    ----------
    microscope_type: str
        microscope type

    Returns
    -------
    module
        loaded module instance

    Raises
    ------
    ValueError
        when `microscope_type` is not known
    '''
    if microscope_type not in SUPPORTED_MICROSCOPE_TYPES:
        raise ValueError(
            'Unknown microscope type "%s".\n'
            'Supported are: "%s"' % (
                microscope_type, '", "'.join(SUPPORTED_MICROSCOPE_TYPES)
            )
        )
    module_name = '%s.%s' % (__name__, microscope_type)
    return importlib.import_module(module_name)


def get_microscope_type_regex(microscope_type, as_string=False):
    '''Gets regular expression patterns for the identification of microscope
    image files and microscope metadata files for a given `microscope_type`.

    Parameters
    ----------
    microscope_type: str
        microscope type
    as_string: bool, optional
        whether regex pattern should be returned as strings (default: ``False``)

    Returns
    -------
    Tuple[_sre.SRE_Pattern or str]
        regex pattern for image and metadata files
    '''
    module = import_microscope_type_module(microscope_type)
    if as_string:
        return (
            module.IMAGE_FILE_REGEX_PATTERN,
            module.METADATA_FILE_REGEX_PATTERN
        )
    else:
        return (
            re.compile(module.IMAGE_FILE_REGEX_PATTERN),
            re.compile(module.METADATA_FILE_REGEX_PATTERN)
        )


def metadata_reader_factory(microscope_type):
    '''Gets the `microscope_type`-specific implementation of
    :class:`MetadataReader <tmlib.workflow.metaconfig.base.MetadataReader>`.

    Parameters
    ----------
    microscope_type: str
        microscope type

    Returns
    -------
    Union[classobj, None]
        metadata reader class in case one is implemented
    '''
    module = import_microscope_type_module(microscope_type)
    reader_cls = None
    for k, v in vars(module).iteritems():
        if inspect.isclass(v):
            if (MetadataReader in inspect.getmro(v) and
                    not inspect.isabstract(v)):
                reader_cls = v
                break
    if reader_cls is None:
        logger.warn(
            'module "%s" does not implement a MetadataReader class',
            module.__name__
        )
    return reader_cls


def metadata_handler_factory(microscope_type):
    '''Gets the `microscope_type`-specific implementation of
    :class:`tmlib.workflow.metaconfig.base.MetadataHandler`.

    Parameters
    ----------
    microscope_type: str
        microscope type

    Returns
    -------
    classobj

    Raises
    ------
    AttributeError
        when the `miroscope_type`-specific module does not implement a handler
        class
    '''
    module = import_microscope_type_module(microscope_type)
    handler_cls = None
    for k, v in inspect.getmembers(module):
        if inspect.isclass(v) and MetadataHandler in v.__bases__:
            handler_cls = v
            break 
    if handler_cls is None:
        raise AttributeError(
            'Module "%s" does not implement a MetadataHandler class.' %
            module.__name__
        )
    return handler_cls
