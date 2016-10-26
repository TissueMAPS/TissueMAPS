import re
import importlib
import inspect

from tmlib import __version__
from tmlib.workflow.metaconfig.base import MetadataReader
from tmlib.workflow.metaconfig.base import MetadataHandler


__fullname__ = 'Configuration of image metadata'

__description__ = '''Configuration of extracted OMEXML metadata
    and integration with additional microscope-specific information about
    the image acquisition process.
'''

__logo__ = '''
            _                     __ _
  _ __  ___| |_ __ _ __ ___ _ _  / _(_)__ _         {name} ({version})
 | '  \/ -_)  _/ _` / _/ _ \ ' \|  _| / _` |        {fullname}
 |_|_|_\___|\__\__,_\__\___/_||_|_| |_\__, |        https://github.com/TissueMAPS/TmLibrary
                                      |___/
'''.format(name=__name__, version=__version__, fullname=__fullname__)


SUPPORTED_MICROSCOPE_TYPES = {
    'visiview', 'cellvoyager', 'axio', 'default', 'metamorph', 'niselements',
    'incell', 'imc'
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
            'Supported are: "%s"' % '", "'.join(SUPPORTED_MICROSCOPE_TYPES)
        )
    module_name = '%s.%s' % (__name__, microscope_type)
    return importlib.import_module(module_name)


def get_microscope_type_regex(microscope_type, as_string=False):
    '''Gets regular expression patterns for the identification of microscope
    image files and microscope metadata files for a given `microscope_type`.

    Paramaters
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
    :class:`tmlib.workflow.metaconfig.base.MetadataReader`.

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
        when the `miroscope_type`-specific module does not implement a reader
        class
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
        raise AttributeError(
            'Module "%s" does not implement a MetadataReader class.' %
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
    for k, v in vars(module).iteritems():
        if inspect.isclass(v):
            if (MetadataHandler in inspect.getmro(v) and
                    not inspect.isabstract(v)):
                handler_cls = v
                break
    if handler_cls is None:
        raise AttributeError(
            'Module "%s" does not implement a MetadataHandler class.' %
            module.__name__
        )
    return handler_cls
