# Copyright 2016, 2019 Markus D. Herrmann, University of Zurich
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
from itertools import chain
import multiprocessing.dummy as mp

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
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
        # save parameters for late initialization (when `self._session` is first accessed)
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._ca_bundle = ca_bundle

        self._real_session = None
        self._real_adapter = None
        self._real_base_url = None

    def _init_session(self):
        '''
        Delayed initialization of Requests Session object.

        This is done in order *not* to share the Session object across
        a multiprocessing pool.
        '''
        self._real_session = requests.Session()
        # see: https://www.peterbe.com/plog/best-practice-with-retries-with-requests
        retry = Retry(
            total=3,
            backoff_factor=0.3,
            status_forcelist=[104],
        )
        adapter = HTTPAdapter(max_retries=retry)
        self._real_session.mount('http://', adapter)
        # FIXME: this fails when one runs HTTPS on non-standard ports,
        # e.g. https://tissuemaps.example.org:8443/
        if self._port == 443:
            logger.debug('initializing HTTPS session')
            self._real_base_url = 'https://{host}:{port}'.format(host=self._host, port=self._port)
            self._real_adapter = self._real_session.adapters['https://']
            if self._ca_bundle is not None:
                logger.debug('use CA bundle: %s', self._ca_bundle)
                ca_bundle = os.path.expanduser(os.path.expandvars(self._ca_bundle))
                if not os.path.exists(ca_bundle):
                    raise OSError(
                        'CA bundle file does not exist: {0}'.format(ca_bundle)
                    )
                self._real_session.verify = ca_bundle
        else:
            logger.debug('initializing HTTP session')
            self._real_base_url = 'http://{host}:{port}'.format(host=self._host, port=self._port)
            self._real_adapter = self._real_session.adapters['http://']
        self._real_session.get(self._real_base_url)
        self._real_session.headers.update({'Host': self._host})
        self._login(self._username, self._password)

    @property
    def _session(self):
        '''Return a Requests Session, creating it first if necessary.'''
        if self._real_session is None:
            self._init_session()
        return self._real_session

    @property
    def _adapter(self):
        '''Return a Requests Adapter, creating it first if necessary.'''
        if self._real_adapter is None:
            self._init_session()
        return self._real_adapter

    @property
    def _base_url(self):
        '''Return the base URL for HTTP(S) requests, creating session first if necessary.'''
        if self._real_base_url is None:
            self._init_session()
        return self._real_base_url


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

    def _parallelize(self, work, processes=2):
        if not processes:
            # use 2x number of available CPUs
            processes = 2 * mp.cpu_count()

        # compute chunk size
        connection_pool_size = self._adapter.poolmanager.connection_pool_kw['maxsize']
        chunksize = max(1, 2 * len(work) // int(connection_pool_size))

        # create process pool and run `func` in parallel
        logger.debug('using %d parallel processes', processes)
        pool = mp.Pool(processes)
        return pool.map(self.__do, work, chunksize)

    @staticmethod
    def __do(work):
        """
        Helper function for `HttpClient._parallelize`.
        """
        fn = work[0]
        args = work[1:]
        return fn(*args)
