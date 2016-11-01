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

from tmclient.errors import ServerError


logger = logging.getLogger(__name__)


class HttpClient(object):

    '''Abstract base class for RESTful interaction with the
    TissueMAPS server.
    '''

    __metaclass__ = ABCMeta

    def __init__(self, host_name, user_name, password=None):
        '''
        Parameters
        ----------
        host_name: str
            name of the TissueMAPS instance
        user_name: str
            name of the TissueMAPS user
        password: str, optional
            password for `username` (default: ``None``)
        '''
        self.base_url = 'http://%s' % host_name
        self.session = requests.Session()
        self.session.get(self.base_url)
        if password is None:
            password = self._load_credentials(user_name)
        self.login(user_name, password)

    def build_url(self, uri, params={}):
        '''Gets the full URL based on the base URL and the provided
        API `uri`.

        Parameters
        ----------
        uri: str
            URI for TissueMAPS RESTful API
        params: dict, optional
            optional parameters that need to included in the URL

        Returns
        -------
        str
            URL
        '''
        url = self.base_url + uri
        if not params:
            return url
        url = '%s?%s' % (url, urllib.urlencode(params))
        logger.debug('url: %s', url)
        return url

    def _handle_error(self, result):
        if result.status_code != 200:
            message = 'Status %s: %s' % (result.status_code, result.reason)
            try:
                data = result.json()
                if 'description' in data:
                    message += '\n%s: %s' % (
                        data['error'], data['description']
                    )
                else:
                    message += '\n%s: %s' % (
                        data['error']['type'], data['error']['message']
                    )
            except ValueError:
                pass
            raise ServerError(message)

    def _load_credentials(self, username):
        '''Loads password from file.

        The file must be called ``".tmaps_pass.yaml"`` and stored in
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
        '''
        cred_filepath = os.path.expanduser('~/.tmaps_pass.yaml')
        if not os.path.exists(cred_filepath):
            raise OSError('Credentials file ".tmaps_pass.yaml" not found.')
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
        url = self.build_url('/auth')
        payload = {'username': username, 'password': password}
        res = self.session.post(url, json=payload)
        self._handle_error(res)
        self._access_token = res.json()['access_token']
        self.session.headers.update(
            {'Authorization': 'JWT %s' % self._access_token}
        )
