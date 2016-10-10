import os
from abc import ABCMeta
import logging
from ConfigParser import SafeConfigParser

logger = logging.getLogger(__name__)

CONFIG_FILE = os.path.expanduser('~/.tmaps/tissuemaps.cfg')


class TmapsConfig(object):

    '''Abstract base class for `TissueMAPS` configuration settings.

    `TissueMAPS` code is distributed across mutliple Python packages,
    but configuration settings are bundeled in one global config file
    (:py:constant:`tmlib.config.CONFIG_FILE`)
    with an `INI <https://en.wikipedia.org/wiki/INI_file>`_-like file format.

    The environment variable ``TMAPS_CONFIG_FILE`` can be used to overwrite
    the default location of the file.

    Properties defined on this base class are written into the ``DEFAULT``
    section of the file. Each package that requires configuration should
    implement this base class. This will create a separate package-specific
    section in the config file for the derived class.
    '''

    __meta__ = ABCMeta

    def __init__(self):
        if 'TMAPS_CONFIG_FILE' in os.environ:
            self._config_file = os.environ['TMAPS_CONFIG_FILE']
            logger.info(
                'use config file set by environment variable TMAPS_CONFIG_FILE'
            )
        else:
            self._config_file = CONFIG_FILE
            logger.info('use default config file')
        logger.debug('config file: %s', self._config_file)
        if not os.path.exists(self._config_file):
            logger.warn(
                'configuration file does not exist: %s' % self._config_file
            )
        self._config = SafeConfigParser({'home': os.environ['HOME']})
        self._section = self.__class__.__module__.split('.')[0]
        self._config.add_section(self._section)
        self.db_user = 'postgres'
        self.db_host = 'localhost'
        self.db_port = 5432
        self.read()

    def read(self):
        '''Reads the configuration from a file

        See also
        --------
        tmlib.config.CONFIG_FILE
        '''
        logger.info('read config file: "%s"', self._config_file)
        self._config.read(self._config_file)

    def write(self):
        '''Writes the configuration to a file'''
        with open(self._config_file, 'wb') as f:
            self._config.write(f)

    @property
    def db_user(self):
        '''str: database user (default: ``"postgres"``)'''
        return self._config.get('DEFAULT', 'db_user')

    @db_user.setter
    def db_user(self, value):
        if not isinstance(value, basestring):
            raise ValueError(
                'Configuration parameter "db_user" must have type str.'
            )
        self._config.set('DEFAULT', 'db_user', str(value))

    @property
    def db_password(self):
        '''str: database password'''
        return self._config.get('DEFAULT', 'db_password')

    @db_password.setter
    def db_password(self, value):
        if not isinstance(value, basestring):
            raise ValueError(
                'Configuration parameter "db_password" must have type str.'
            )
        self._config.set('DEFAULT', 'db_password', str(value))

    @property
    def db_host(self):
        '''str: database host (default: ``"localhost"``)'''
        return self._config.get('DEFAULT', 'db_host')

    @db_host.setter
    def db_host(self, value):
        if not isinstance(value, basestring):
            raise ValueError(
                'Configuration parameter "db_host" must have type str.'
            )
        self._config.set('DEFAULT', 'db_host', value)

    @property
    def db_port(self):
        '''str: database host (default: ``5432``)'''
        return self._config.getint('DEFAULT', 'db_port')

    @db_port.setter
    def db_port(self, value):
        if not isinstance(value, int):
            raise ValueError(
                'Configuration parameter "db_port" must have type int.'
            )
        self._config.set('DEFAULT', 'db_port', str(value))

    @property
    def db_uri_sqla(self):
        '''str: database URI in `SQLAlchemy` format'''
        return 'postgresql://{user}:{pw}@{host}:{port}/tissuemaps'.format(
            user=self.db_user, pw=self.db_password,
            host=self.db_host, port=self.db_port
        )

    @property
    def db_uri_jdbc(self):
        '''str: database URI in `JDBC` format'''
        return 'postgresql://{host}:{port}/tissuemaps?user={user}:password={pw}'.format(
            user=self.db_user, pw=self.db_password,
            host=self.db_host, port=self.db_port
        )

    @property
    def items(self):
        '''List[Tuple[str, str or int or bool]]: ``(name, value)`` pairs for
        each configuration parameter in the implemented section
        '''
        return self._config.items(self._section)


class LibraryConfig(TmapsConfig):

    '''`TissueMAPS` configuration specific to the `tmlib` package.'''

    def __init__(self):
        super(LibraryConfig, self).__init__()
        self.modules_home = '%(home)s/jtmodules'
        self.storage_home = '%(home)s/experiments'
        self.read()

    @property
    def modules_home(self):
        '''str: absolute path to root directory of local copy of `JtModules`
        repository (default: ``os.path.expanduser("$HOME/jtmodules")``)
        '''
        env_var = 'TMAPS_MODULES_HOME'
        if env_var in os.environ:
            logger.debug(
                'config parameter "modules_home" set by environment variable %s',
                env_var
            )
            return os.environ[env_var]
        else:
            return self._config.get(self._section, 'modules_home')

    @modules_home.setter
    def modules_home(self, value):
        if not isinstance(value, basestring):
            raise TypeError(
                'Configuration parameter "modules_home" must have type str.'
            )
        self._config.set(self._section, 'modules_home', str(value))

    @property
    def storage_home(self):
        '''str: absolute path to root directory of file system storage
        (default: ``os.path.expanduser("$HOME/experiments")``)
        '''
        env_var = 'TMAPS_storage_home'
        if env_var in os.environ:
            logger.debug(
                'config parameter "storage_home" set by environment variable %s',
                env_var
            )
            return os.environ[env_var]
        else:
            return self._config.get(self._section, 'storage_home')

    @storage_home.setter
    def storage_home(self, value):
        if not isinstance(value, basestring):
            raise TypeError(
                'Configuration parameter "storage_home" must have type str.'
            )
        self._config.set(self._section, 'storage_home', str(value))

