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


def import_microscope_specific_module(microscope_type):
    '''Load the module specific to a given microscope type.

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


def metadata_reader_factory(microscope_type):
    '''Return a microscope-specific implementation
    of the :py:class:`tmlib.steps.metaconfig.default.MetadataReader`
    abstract base class.

    Parameters
    ----------
    microscope_type: str
        microscope type

    Returns
    -------
    tmlib.steps.metaconfig.default.MetadataReader
    '''
    module = import_microscope_specific_module(microscope_type)
    class_name = '%sMetadataReader' % microscope_type.capitalize()
    return getattr(module, class_name)


def metadata_handler_factory(microscope_type):
    '''Return a microscope-specific implementation
    of the :py:class:`tmlib.steps.metaconfig.default.MetadataHandler`
    abstract base class.

    Parameters
    ----------
    microscope_type: str
        microscope type

    Returns
    -------
    tmlib.steps.metaconfig.default.MetadataHandler
    '''
    module = import_microscope_specific_module(microscope_type)
    class_name = '%sMetadataHandler' % microscope_type.capitalize()
    return getattr(module, class_name)
