import re
import importlib
from tmlib import __version__

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


def get_microscope_type_regex(microscope_type):
    '''Gets regular expression patterns for the identification of microscope
    image files and microscope metadata files for a given
    `microscope_type`.

    Paramaters
    ----------
    microscope_type: str
        microscope type

    Returns
    -------
    Tuple[_sre.SRE_Pattern]
        regex pattern for image and metadata files
    '''
    module = import_microscope_type_module(microscope_type)
    return (
        re.compile(module.IMAGE_FILE_REGEX_PATTERN), 
        re.compile(module.METADATA_FILE_REGEX_PATTERN)
    )


def metadata_reader_factory(microscope_type):
    '''Gets the implementation
    of the :py:class:`tmlib.workflow.metaconfig.default.MetadataReader`
    abstract base class for the given microscope type.

    Parameters
    ----------
    microscope_type: str
        microscope type

    Returns
    -------
    classobj
    '''
    module = import_microscope_type_module(microscope_type)
    class_name = '%sMetadataReader' % microscope_type.capitalize()
    return getattr(module, class_name)


def metadata_handler_factory(microscope_type):
    '''Gets the implementation of the
    :py:class:`tmlib.workflow.metaconfig.default.MetadataHandler`
    abstract base class for the given microscope type.

    Parameters
    ----------
    microscope_type: str
        microscope type

    Returns
    -------
    classobj
    '''
    module = import_microscope_type_module(microscope_type)
    class_name = '%sMetadataHandler' % microscope_type.capitalize()
    return getattr(module, class_name)
