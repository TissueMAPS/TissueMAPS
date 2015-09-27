from types import ModuleType

'''
Classes for converting configuration settings from different sources
to Python namespaces for convenient indexing.
'''


class TmlibConfiguration(object):

    '''
    Class for configuration settings from a Python module.
    '''

    def __init__(self, cfg_settings):
        '''
        Create a namespace object.

        Parameters
        ----------
        cfg_settings: ModuleType
            configuration settings

        Returns
        -------
        TmlibConfiguration
        '''
        if not isinstance(cfg_settings, ModuleType):
            raise TypeError('Configurations must be a module')
        [
            setattr(self, name, getattr(cfg_settings, name))
            for name in dir(cfg_settings)
            if not name.startswith('__') and not name.endswith('__')
         ]


class UserConfiguration(object):

    '''
    Class for configuration settings from a Python dictionary.
    '''

    def __init__(self, cfg_settings):
        '''
        Create a namespace object.

        Parameters
        ----------
        cfg_settings: dict
            configuration settings

        Returns
        -------
        UserConfiguration
        '''
        [
            setattr(self, name, value)
            for name, value in cfg_settings.iteritems()
        ]

    # TODO: create defined attributes with setters for required information
    # and check their type and value
