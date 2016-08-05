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

    def __init__(self, hostname):
        '''
        Parameters
        ----------
        hostname: str
            hostname of the TissueMAPS instance
        '''
        self.base_url = 'http://%s' % hostname
        self.session = requests.Session()
        self.session.get(self.base_url)

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
                message += '\n%s: %s' % (
                    data['error']['type'], data['error']['message']
                )
                # if 'description' in json:
                #     message += json['description']
            except ValueError:
                pass
            raise ServerError(message)

    def load_credentials(self, username):
        '''Loads password from file.

        The file must be called ``".tmaps_pass.yaml"`` and stored in
        the home directory. It must provide a YAML mapping where
        keys are usernames and the values the corresponding
        passwords.

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
        if os.path.exists(cred_filepath):
            with open(cred_filepath) as cred_file:
                user_credentials = yaml.load(cred_file.read())
        return user_credentials[username]

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
