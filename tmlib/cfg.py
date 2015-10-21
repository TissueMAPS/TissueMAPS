import os
import logging
from .plate import Plate

logger = logging.getLogger(__name__)

'''
CONFIGURATION SETTINGS

Describe the experimental layout (directory structure and filename nomenclature)
by Python format strings. The keywords are replaced by the program with the
values of attributes of the configuration classes.
'''

USER_CFG_FILE_FORMAT = '{experiment_dir}{sep}user.cfg.yml'

LAYER_NAME_FORMAT = 't{t:0>3}_c{c:0>3}_z{z:0>3}'

IMAGE_NAME_FORMAT = '{plate_name}_t{t:0>3}_{w}_y{y:0>3}_x{x:0>3}_c{c:0>3}_z{z:0>3}.png'


class UserConfiguration(object):

    '''
    Class for configuration settings provided by the user.
    '''

    PERSISTENT_ATTRS = {
        'sources_dir', 'plates_dir', 'layers_dir', 'plate_format'
    }

    def __init__(self, experiment_dir):
        '''
        Initialize an instance of class UserConfiguration.

        Parameters
        ----------
        experiment_dir: str
            absolute path to experiment directory
        '''
        self.experiment_dir = experiment_dir
        self._sources_dir = None
        self._plates_dir = None
        self._layers_dir = None

    @property
    def sources_dir(self):
        '''
        Returns
        -------
        str
            absolute path to the directory where source files are located

        See also
        --------
        `tmlib.source.PlateSource`_
        `tmlib.source.PlateAcquisition`_
        '''
        if self._sources_dir is None:
            self._sources_dir = os.path.join(self.experiment_dir, 'sources')
            logger.debug('set default "sources" directory: %s',
                         self._sources_dir)
        return self._sources_dir

    @sources_dir.setter
    def sources_dir(self, value):
        if not(isinstance(value, basestring) or value is None):
            raise TypeError('Attribute "plates_dir" must have type str')
        if value is None:
            self._sources_dir = None
        else:
            self._sources_dir = str(value)

    @property
    def plates_dir(self):
        '''
        Returns
        -------
        str
            absolute path to the directory where extracted files are located
            (grouped per *plate* and *cycle*)

        See also
        --------
        `tmlib.plate.Plate`_
        `tmlib.cycle.Cycle`_
        '''
        if self._plates_dir is None:
            self._plates_dir = os.path.join(self.experiment_dir, 'plates')
            logger.debug('set default "plates" directory: %s',
                         self._plates_dir)
        return self._plates_dir

    @plates_dir.setter
    def plates_dir(self, value):
        if not(isinstance(value, basestring) or value is None):
            raise TypeError('Attribute "plates_dir" must have type str')
        if value is None:
            self._plates_dir = None
        else:
            self._plates_dir = str(value)

    @property
    def layers_dir(self):
        '''
        Returns
        -------
        str
            absolute path to the directory where image pyramids and associated
            data are stored

        See also
        --------
        `tmlib.illuminati.layers`_
        `tmlib.jterator.data_fusion`_
        '''
        if self._layers_dir is None:
            self._layers_dir = os.path.join(self.experiment_dir, 'layers')
            logger.debug('set default "layers" directory: %s',
                         self._layers_dir)
        return self._layers_dir

    @layers_dir.setter
    def layers_dir(self, value):
        if not(isinstance(value, basestring) or value is None):
            raise TypeError('Attribute "layers_dir" must have type str')
        if value is None:
            self._layers_dir = None
        else:
            self._layers_dir = str(value)

    @property
    def plate_format(self):
        '''
        Returns
        -------
        int
            plate format, i.e. total number of wells per plate
        '''
        return self._plate_format

    @plate_format.setter
    def plate_format(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "plate_format" must have type int')
        if value not in Plate.SUPPORTED_PLATE_FORMATS:
            raise ValueError(
                    'Attribute "plate_format" can be set to "%s"'
                    % '"or "'.join(Plate.SUPPORTED_PLATE_FORMATS))
        self._plate_format = value

    def __iter__(self):
        pass

    @staticmethod
    def set(experiment_dir, cfg_settings):
        '''
        Set user configuration based on key-value pairs of dictionary.

        Parameters
        ----------
        experiment_dir: str
            absolute path to experiment directory
        cfg_settings: dict
            user configuration settings

        Returns
        -------
        UserConfiguration
            experiment-specific user configuration object
        '''
        cfg = UserConfiguration(experiment_dir)
        for k, v in cfg_settings.iteritems():
            if k in cfg.PERSISTENT_ATTRS:
                setattr(cfg, k, v)
        return cfg
