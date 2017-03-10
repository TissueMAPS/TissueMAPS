# Copyright 2016 Markus D. Herrmann, University of Zurich
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import yaml
import logging
import urllib
import requests
from abc import ABCMeta


logger = logging.getLogger(__name__)


class HttpClient(object):

    '''Abstract base class for HTTP interface.'''

    __metaclass__ = ABCMeta

    def __init__(self, host, port, user_name, password=None):
        '''
        Parameters
        ----------
        host: str
            name of the TissueMAPS host
        port: int
            number of the port to which TissueMAPS server listens
        user_name: str
            name of the TissueMAPS user
        password: str, optional
            password for `username` (default: ``None``)
        '''
        self._base_url = 'http://%s:%d' % (host, port)
        self._session = requests.Session()
        self._session.get(self._base_url)
        if password is None:
            password = self._load_credentials(user_name)
        self.login(user_name, password)

    def _build_url(self, route, params={}):
        '''Builds the full URL based on the base URL (``http://<host>:<port>``)
        and the provided `route`.

        Parameters
        ----------
        route: str
            route used by the TissueMAPS RESTful API
        params: dict, optional
            optional parameters that need to be included in the URL query string

        Returns
        -------
        str
            URL
        '''
        url = self._base_url + route
        if not params:
            logger.debug('url: %s', url)
            return url
        url = '%s?%s' % (url, urllib.urlencode(params))
        logger.debug('url: %s', url)
        return url

    def _load_credentials(self, username):
        '''Loads password for `username` from file.

        The file must be called ``~/.tm_pass`` and stored in
        the home directory. It must provide a YAML mapping where
        keys are usernames and the values the corresponding passwords.

        Parameters
        ----------
        username: str
            name of the TissueMAPS user

        Returns
        -------
        str
            password for the given user

        Raises
        ------
        OSError
            when the file does not exist
        ValueError
            when the file cannot be parsed
        KeyError
            when `username` is not found in file
        '''
        cred_filepath = os.path.expanduser('~/.tm_pass')
        if not os.path.exists(cred_filepath):
            raise OSError('Credentials file "~/.tm_pass" not found.')
        try:
            with open(cred_filepath) as cred_file:
                credentials = yaml.load(cred_file.read())
        except Exception as err:
            raise ValueError(
                'Credentials could not be read from file: %s.' % err
            )
        if username not in credentials:
            raise KeyError('No credentials found for user "%s".' % username)
        return credentials[username]


    def login(self, username, password):
        '''Authenticates the user.

        Parameters
        ----------
        username: str
            name of the TissueMAPS user
        password: str
            password of the user
        '''
        logger.debug('login in as: "%s"' % username)
        url = self._build_url('/auth')
        payload = {'username': username, 'password': password}
        res = self._session.post(url, json=payload)
        res.raise_for_status()
        self._access_token = res.json()['access_token']
        self._session.headers.update(
            {'Authorization': 'JWT %s' % self._access_token}
        )
