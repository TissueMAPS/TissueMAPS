import importlib
from tmlib import __version__

logo = '''
            _                     __ _
  _ __  ___| |_ __ _ __ ___ _ _  / _(_)__ _         metaconfig (tmlib %s)
 | '  \/ -_)  _/ _` / _/ _ \ ' \|  _| / _` |        Configure OMEXML metadata.
 |_|_|_\___|\__\__,_\__\___/_||_|_| |_\__, |        https://github.com/TissueMAPS/TmLibrary
                                      |___/
''' % __version__


SUPPORTED_MICROSCOPE_TYPES = {'visiview', 'cellvoyager', 'default'}


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
    Tuple[str]
        regex pattern for image and metadata files
    '''
    module = import_microscope_type_specific_module(microscope_type)
    return (module.IMAGE_FILE_REGEX_PATTERN, module.METADATA_FILE_REGEX_PATTERN)


def metadata_reader_factory(microscope_type):
    '''Return the implementation
    of the :py:class:`tmlib.workflow.metaconfig.default.MetadataReader`
    abstract base class for the given microscope type.

    Parameters
    ----------
    microscope_type: str
        microscope type

    Returns
    -------
    tmlib.workflow.metaconfig.default.MetadataReader
    '''
    module = import_microscope_type_module(microscope_type)
    class_name = '%sMetadataReader' % microscope_type.capitalize()
    return getattr(module, class_name)


def metadata_handler_factory(microscope_type):
    '''Return the implementation of the
    :py:class:`tmlib.workflow.metaconfig.default.MetadataHandler`
    abstract base class for the given microscope type.

    Parameters
    ----------
    microscope_type: str
        microscope type

    Returns
    -------
    tmlib.workflow.metaconfig.default.MetadataHandler
    '''
    module = import_microscope_type_module(microscope_type)
    class_name = '%sMetadataHandler' % microscope_type.capitalize()
    return getattr(module, class_name)
