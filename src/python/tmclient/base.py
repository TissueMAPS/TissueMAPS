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
import logging
from abc import ABCMeta
from threading import Thread
from itertools import chain

import yaml
import requests
try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode


logger = logging.getLogger(__name__)


class HttpClient(object):

    '''Abstract base class for HTTP client interface.'''

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
            password for `user_name` (may alternatively provided via the
            ``tm_pass`` file)
        '''
        self._session = requests.Session()
        if port == 443:
            self._base_url = 'https://{host}:{port}'.format(host=host, port=port)
            self._adapter = self._session.adapters['https://']
        else:
            self._base_url = 'http://{host}:{port}'.format(host=host, port=port)
            self._adapter = self._session.adapters['http://']
        self._session.get(self._base_url)
        if password is None:
            logger.debug('no password provided')
            password = self._load_credentials(user_name)
        self._session.headers.update({'Host': host})
        self._login(user_name, password)

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
        url = '{url}?{params}'.format(url=url, params=urlencode(params))
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
        logger.debug('trying to obtain credentials from "~/.tm_pass" file')
        cred_filepath = os.path.expandvars(os.path.join('$HOME', '.tm_pass'))
        if not os.path.exists(cred_filepath):
            raise IOError(
                'No credentials provided and tm_pass file not found: {0}'.format(
                    cred_filepath
                )
            )
        try:
            with open(cred_filepath) as f:
                credentials = yaml.load(f.read())
        except Exception as err:
            raise IOError(
                'Could not be read credentials from file:\n{0}'.format(str(err))
            )
        if username not in credentials:
            raise ValueError(
                'No credentials provided for user "{0}"'.format(username)
            )
        return credentials[username]

    def _login(self, username, password):
        '''Authenticates a TissueMAPS user.

        Parameters
        ----------
        username: str
            name
        password: str
            password
        '''
        logger.debug('login in as user "%s"' % username)
        url = self._build_url('/auth')
        payload = {'username': username, 'password': password}
        res = self._session.post(url, json=payload)
        res.raise_for_status()
        self._access_token = res.json()['access_token']
        self._session.headers.update(
            {'Authorization': 'JWT %s' % self._access_token}
        )

    def _parallelize(self, func, args):
        logger.debug('parallelize request')
        pool_size = self._adapter.poolmanager.connection_pool_kw['maxsize']
        n = len(args) / int(pool_size / 2)
        n = max([n, 1])
        arg_batches = [args[i:i + n] for i in range(0, len(args), n)]

        def wrapper(func, batch):
            for args in batch:
                func(*args)

        threads = []
        for batch in arg_batches:
            logger.debug('start thread #%d', i)
            # TODO: use queue or generator?
            t = Thread(target=wrapper, args=(func, batch))
            # TODO: use Event
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

