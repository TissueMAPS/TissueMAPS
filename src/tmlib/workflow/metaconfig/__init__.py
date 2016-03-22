import re
import importlib
from ... import __version__

logo = '''
            _                     __ _
  _ __  ___| |_ __ _ __ ___ _ _  / _(_)__ _         metaconfig (tmlib %s)
 | '  \/ -_)  _/ _` / _/ _ \ ' \|  _| / _` |        Configure OMEXML metadata.
 |_|_|_\___|\__\__,_\__\___/_||_|_| |_\__, |        https://github.com/TissueMAPS/TmLibrary
                                      |___/
''' % __version__


SUPPORTED_MICROSCOPE_TYPES = {'visiview', 'cellvoyager'}


def metadata_handler_factory(microscope_type):
    '''
    Return the module as well as the implementation
    of the :py:class:`tmlib.steps.metaconfig.default.MetadataHandler`
    abstract base class for a given microscope type.

    Parameters
    ----------
    microscope_type: str
        microscope type

    Returns
    -------
    Tuple[module, tmlib.steps.metaconfig.default.MetadataHandler]

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
    module = importlib.import_module(module_name)
    class_name = '%sMetadataHandler' % microscope_type.capitalize()
    metaclass_instance = getattr(module, class_name)
    return (module, metaclass_instance)
