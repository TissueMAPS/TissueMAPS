import os
import logging
import datetime

from tmlib.config import TmapsConfig

logger = logging.getLogger(__name__)


class ServerConfig(TmapsConfig):

    '''`TissueMAPS` configuration specific to the `tmserver` package.'''

    def __init__(self):
        super(ServerConfig, self).__init__()
        self.log_file = '%(home)s/.tmaps/tmserver.log'
        self.log_level = logging.INFO
        self.log_max_bytes = 2048000
        self.log_n_backups = 10
        self.secret_key = 'default_secret_key'
        self.jwt_expiration_delta = datetime.timedelta(hours=6)
        self.use_spark = False
        self.spark_master = 'local'

    @property
    def log_file(self):
        '''str: absolute path to file for the TissueMAPS server application log
        (default: ``os.path.expanduser("$HOME/.tmaps/tmserver.log")``)
        '''
        return self._config.get(self._section, 'log_file')

    @log_file.setter
    def log_file(self, value):
        if not isinstance(value, str):
            raise TypeError(
                'Configuration parameter "log_file" must have type str.'
            )
        self._config.set(self._section, 'log_file', str(value))

    @property
    def log_level(self):
        '''int: verbosity level for `TissueMAPS` loggers
        (default: ``logging.INFO``)
        '''
        level = self._config.get(self._section, 'log_level')
        return getattr(logging, level)

    @log_level.setter
    def log_level(self, value):
        if not isinstance(value, int):
            raise TypeError(
                'Configuration parameter "log_level" must have type int.'
            )
        level_mapper = {
            logging.NOTSET: 'NOTSET',
            logging.DEBUG: 'DEBUG',
            logging.INFO: 'INFO',
            logging.WARNING: 'WARNING',
            logging.ERROR: 'ERROR',
            logging.CRITICAL: 'CRITICAL'
        }
        if value not in level_mapper:
            raise ValueError('Unkown logging level.')
        self._config.set(self._section, 'log_level', level_mapper[value])

    @property
    def log_max_bytes(self):
        '''int: maximum number of bytes that should be logged
        (default: ``2048000``)
        '''
        return self._config.getint(self._section, 'log_max_bytes')

    @log_max_bytes.setter
    def log_max_bytes(self, value):
        if not isinstance(value, int):
            raise TypeError(
                'Configuration parameter "log_max_bytes" must have type int.'
            )
        self._config.set(self._section, 'log_max_bytes', str(value))

    @property
    def log_n_backups(self):
        '''int: maximum number of log backups (default: ``10``)
        '''
        return self._config.getint(self._section, 'log_n_backups')

    @log_n_backups.setter
    def log_n_backups(self, value):
        if not isinstance(value, int):
            raise TypeError(
                'Configuration parameter "log_n_backups" must have type int.'
            )
        self._config.set(self._section, 'log_n_backups', str(value))

    @property
    def secret_key(self):
        '''str: secret key (default: ``"default_secret_key"``)
        '''
        return self._config.get(self._section, 'secret_key')

    @secret_key.setter
    def secret_key(self, value):
        if not isinstance(value, basestring):
            raise TypeError(
                'Configuration parameter "secret_key" must have type str.'
            )
        self._config.set(self._section, 'secret_key', str(value))

    @property
    def jwt_expiration_delta(self):
        '''datetime.timedelta: time interval until JSON web token expires
        (default: ``datetime.timedelta(hours=6)``)
        '''
        t_string = self._config.get(self._section, 'jwt_expiration_delta')
        t = datetime.datetime.strptime(t_string, '%H:%M:%S')
        return datetime.timedelta(
            hours=t.hour, minutes=t.minute, seconds=t.second
        )

    @jwt_expiration_delta.setter
    def jwt_expiration_delta(self, value):
        if not isinstance(value, datetime.timedelta):
            raise TypeError(
                'Configuration parameter "jwt_expiration_delta" must have type '
                'datetime.timedelta'
            )
        self._config.set(self._section, 'jwt_expiration_delta', str(value))

    @property
    def spark_master(self):
        '''str: URL for `Apache Spark` master node (default: ``"local"``)'''
        return self._config.get(self._section, 'spark_master')

    @spark_master.setter
    def spark_master(self, value):
        if not isinstance(value, basestring):
            raise TypeError(
                'Configuration parameter "spark_master" must have type str.'
            )
        vals = {'local', 'yarn'}
        if value not in vals:
            raise ValueError(
                'Configuration parameter "spark_master" must be one of the '
                'following: "%s"' % '", "'.join(vals)
            )
        self._config.set(self._section, 'spark_master', str(value))

    @property
    def use_spark(self):
        '''bool: whether `Apache Spark` should be used for processing
        (default: ``False``)
        '''
        return self._config.getboolean(self._section, 'use_spark')

    @use_spark.setter
    def use_spark(self, value):
        if not isinstance(value, bool):
            raise TypeError(
                'Configuration parameter "use_spark" must have type bool.'
            )
        self._config.set(self._section, 'use_spark', str(value).lower())
