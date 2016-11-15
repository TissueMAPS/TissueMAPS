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
import os
from abc import ABCMeta
import logging
from ConfigParser import SafeConfigParser
from ConfigParser import NoOptionError

logger = logging.getLogger(__name__)


CONFIG_FILE = os.path.expanduser('~/.tmaps/tissuemaps.cfg')
DEFAULT_LIB = 'pandas'
IMPLEMENTED_LIBS = {DEFAULT_LIB, 'spark'}


class TmapsConfig(object):

    '''Abstract base class for `TissueMAPS` configuration settings.

    `TissueMAPS` code is distributed across mutliple Python packages,
    but configuration settings are bundeled in one global config file
    (:constant:`CONFIG_FILE <tmlib.config.CONFIG_FILE>`)
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
        self._config = SafeConfigParser()
        self._section = self.__class__.__module__.split('.')[0]
        if not self._config.has_section(self._section):
            self._config.add_section(self._section)
        self.db_user = 'postgres'
        self.db_host = 'localhost'
        self.db_port = 5432

    def read(self):
        '''Reads the configuration from a file

        See Also
        --------
        :const:`tmlib.config.CONFIG_FILE`
        '''
        logger.debug('read config file: "%s"', self._config_file)
        try:
            self._config.read(self._config_file)
        except OSError:
            logger.warn('no configuration file found')

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
        '''str: database password

        Note
        ----
        Must be an alphanumeric string without any special characters.
        '''
        try:
            # Workaround special characters like %
            return self._config.get('DEFAULT', 'db_password')
        except NoOptionError:
            raise ValueError(
                'Parameter "db_password" is required in "DEFAULT" '
                'section of configuration file.'
            )

    @db_password.setter
    def db_password(self, value):
        if not isinstance(value, basestring):
            raise ValueError(
                'Configuration parameter "db_password" must have type str.'
            )
        if not value.isalnum():
            raise ValueError(
                'Argument "db_password" must be alphanumeric.'
            )
        self._config.set('DEFAULT', 'db_password', value)

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
        '''str: database port (default: ``5432``)'''
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
    def db_uri_spark(self):
        '''str: database URI in `JDBC` format as required by `Spark`'''
        return 'jdbc:postgresql://{host}:{port}/tissuemaps?user={user}&password={pw}'.format(
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
        self.modules_home = '~/jtmodules'
        self.storage_home = '/data/experiments'
        self.tool_library = DEFAULT_LIB
        self.spark_master = 'local'
        self.read()

    @property
    def modules_home(self):
        '''str: absolute path to root directory of local copy of `JtModules`
        repository (default: ``"~/jtmodules"``)
        '''
        return os.path.expandvars(os.path.expanduser(
            self._config.get(self._section, 'modules_home')
        ))

    @modules_home.setter
    def modules_home(self, value):
        if not isinstance(value, basestring):
            raise TypeError(
                'Configuration parameter "modules_home" must have type str.'
            )
        self._config.set(
            self._section, 'modules_home',
            os.path.expandvars(os.path.expanduser(str(value)))
        )

    @property
    def storage_home(self):
        '''str: absolute path to root directory of file system storage
        (default: ``"/data/experiments"``)'''
        return os.path.expandvars(os.path.expanduser(
            self._config.get(self._section, 'storage_home')
        ))

    @storage_home.setter
    def storage_home(self, value):
        if not isinstance(value, basestring):
            raise TypeError(
                'Configuration parameter "storage_home" must have type str.'
            )
        self._config.set(self._section, 'storage_home', str(value))

    @property
    def spark_master(self):
        '''str: name of the `Apache Spark` master
        (choices: ``{"local", "yarn"}``, default: ``"local"``)
        '''
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
    def spark_jdbc_driver(self):
        '''str: path to the `PostgreSQL` JDBC driver jar file

        The driver can be downloaded from the
        `PostgreSQL website <https://jdbc.postgresql.org/download.html>`_.
        '''
        return os.path.expanduser(os.path.expandvars(
            self._config.get(self._section, 'spark_jdbc_driver')
        ))

    @spark_jdbc_driver.setter
    def spark_jdbc_driver(self, value):
        if not isinstance(value, basestring):
            raise TypeError(
                'Configuration parameter "spark_jdbc_driver" must have type str.'
            )
        value = os.path.expanduser(os.path.expandvars(value))
        if not os.path.exists(value):
            raise OSError(
                'JDBC driver does not exist: %s', value
            )
        self._config.set(self._section, 'spark_jdbc_driver', str(value))

    @property
    def tool_library(self):
        '''str: library that should be used for processing tool requests
        requests (default: ``"pandas"``, options: ``{"pandas", "spark"}``)
        '''
        return self._config.get(self._section, 'tool_library')

    @tool_library.setter
    def tool_library(self, value):
        if not isinstance(value, basestring):
            raise TypeError(
                'Configuration parameter "tool_library" must have type str.'
            )
        if value not in IMPLEMENTED_LIBS:
            raise ValueError(
                'Configuration parameter "tool_library" can be one of the '
                'following: "%s"' % '", "'.join(IMPLEMENTED_LIBS)
            )
        self._config.set(self._section, 'tool_library', str(value))
