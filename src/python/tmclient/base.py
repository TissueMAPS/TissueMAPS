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

import requests
try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode


logger = logging.getLogger(__name__)


class HttpClient(object):

    '''Abstract base class for HTTP client interface.'''

    __metaclass__ = ABCMeta

    def __init__(self, host, port, username, password, ca_bundle=None):
        '''
        Parameters
        ----------
        host: str
            name of the TissueMAPS host
        port: int
            number of the port to which TissueMAPS server listens
        username: str
            name of the TissueMAPS user
        password: str
            password for `username`
        ca_bundle: str, optional
            path to a CA bundle file in Privacy Enhanced Mail (PEM) format;
            only used with HTTPS when `port` is set to ``443``
        '''
        self._session = requests.Session()
        if port == 443:
            logger.debug('use HTTPS protocol')
            self._base_url = 'https://{host}:{port}'.format(host=host, port=port)
            self._adapter = self._session.adapters['https://']
            if ca_bundle is not None:
                logger.debug('use CA bundle: %s', ca_bundle)
                ca_bundle = os.path.expanduser(os.path.expandvars(ca_bundle))
                if not os.path.exists(ca_bundle):
                    raise OSError(
                        'CA bundle file does not exist: {0}'.format(ca_bundle)
                    )
                self._session.verify = ca_bundle
        else:
            logger.debug('use HTTP protocol')
            self._base_url = 'http://{host}:{port}'.format(host=host, port=port)
            self._adapter = self._session.adapters['http://']
        self._session.get(self._base_url)
        self._session.headers.update({'Host': host})
        self._login(username, password)

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
        n = len(args) // int(pool_size / 2)
        n = max([n, 1])
        arg_batches = [args[i:i + n] for i in range(0, len(args), n)]

        def wrapper(func, batch):
            for args in batch:
                func(*args)

        threads = []
        for i, batch in enumerate(arg_batches):
            logger.debug('start thread #%d', i)
            # TODO: use queue or generator?
            t = Thread(target=wrapper, args=(func, batch))
            # TODO: use Event
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

