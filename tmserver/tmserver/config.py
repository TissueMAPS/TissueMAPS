# TmServer - TissueMAPS server application.
# Copyright (C) 2016-2018 University of Zurich.
# Copyright (C) 2018  University of Zurich
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
import ConfigParser
import os
import logging
import datetime

from gc3libs.quantity import Duration

from tmlib.config import TmapsConfig

from util import which

logger = logging.getLogger(__name__)


class ServerConfig(TmapsConfig):
    """`TissueMAPS` configuration specific to the `tmserver` package."""

    def __init__(self):
        super(ServerConfig, self).__init__()
        self.logging_verbosity = 2
        self.secret_key = 'default_secret_key'
        self.jwt_expiration_delta = datetime.timedelta(hours=72)
        self.read()

    @property
    def jobdaemon(self):
        try:
            return self._config.get(self._section, 'jobdaemon')
        except ConfigParser.NoOptionError:
            # search it on the shell's $PATH
            jobdaemon = which('tm_jobdaemon.py')
            if jobdaemon is None:
                raise LookupError(
                    "No value specified for configuration option `[{0}]{1}`,"
                    " and cannot find `tm_jobdaemon.py` on the shell search PATH."
                    .format(self._section, 'jobdaemon'))
            # remember it for next invocation
            self._config.set(self._section, 'jobdaemon', jobdaemon)
            return self._config.get(self._section, 'jobdaemon')

    @property
    def jobdaemon_host(self):
        try:
            return self._config.get(self._section, 'jobdaemon_host')
        except ConfigParser.NoOptionError:
            # remember it for next invocation
            self._config.set(self._section, 'jobdaemon_host', 'localhost')
            return self._config.get(self._section, 'jobdaemon_host')

    @property
    def jobdaemon_port(self):
        try:
            return self._config.get(self._section, 'jobdaemon_port')
        except ConfigParser.NoOptionError:
            # remember it for next invocation
            self._config.set(self._section, 'jobdaemon_port', '9197')
            return self._config.get(self._section, 'jobdaemon_port')

    @property
    def jobdaemon_session(self):
        try:
            return self._config.get(self._section, 'jobdaemon_session')
        except ConfigParser.NoOptionError:
            # remember it for next invocation
            self._config.set(self._section, 'jobdaemon_session', os.getcwd())
            return self._config.get(self._section, 'jobdaemon_session')

    @property
    def jobdaemon_url(self):
        """
        Build connection URL from ``jobdaemon_host`` and ``jobdaemon_port``.
        """
        return ('http://{host}:{port}'
                .format(host=self.jobdaemon_host,
                        port=self.jobdaemon_port))

    @property
    def logging_verbosity(self):
        '''int: verbosity level for loggers (default: ``2``)

        See also
        --------
        :func:`tmlib.log.map_logging_verbosity`
        '''
        return self._config.getint(self._section, 'logging_verbosity')

    @logging_verbosity.setter
    def logging_verbosity(self, value):
        if not isinstance(value, int):
            raise TypeError(
                'Configuration parameter "logging_verbosity" must have type int.'
            )
        self._config.set(self._section, 'logging_verbosity', str(value))

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
        (default: ``datetime.timedelta(hours=72)``)
        '''
        t = Duration(self._config.get(
            self._section, 'jwt_expiration_delta'))
        return datetime.timedelta(seconds=t.amount(Duration.second))

    @jwt_expiration_delta.setter
    def jwt_expiration_delta(self, value):
        if not isinstance(value, datetime.timedelta):
            raise TypeError(
                'Configuration parameter "jwt_expiration_delta" must have type '
                'datetime.timedelta'
            )
        self._config.set(self._section, 'jwt_expiration_delta', str(value))
