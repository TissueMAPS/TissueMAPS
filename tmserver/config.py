# TmServer - TissueMAPS server application.
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
import logging
import datetime

from tmlib.config import TmapsConfig

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

