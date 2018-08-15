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
import getpass


logger = logging.getLogger(__name__)


def load_credentials_from_file(username):
    '''Loads password for `username` from a file.

    The file must be called ``.tm_pass`` and stored in
    the home directory. It must provide a YAML mapping where
    keys are usernames and values the corresponding passwords.

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
    SyntaxError
        when the file content cannot be parsed
    KeyError
        when the file does not contains a password for `username`

    Warning
    -------
    This is not safe! Passwords are stored in plain text.
    '''
    filename = os.path.expandvars(os.path.join('$HOME', '.tm_pass'))
    try:
        with open(filename) as f:
            credentials = yaml.load(f.read())
    except OSError as err:
        raise OSError(
            'No credentials file:\n{0}'.format(filename)
        )
    except Exception as err:
        raise SyntaxError(
            'Could not be read credentials from file:\n{0}'.format(str(err))
        )
    if username not in credentials:
        raise KeyError(
            'No credentials provided for user "{0}"'.format(username)
        )
    return credentials[username]


def prompt_for_credentials(username):
    '''Prompt `username` for password.

    Parameters
    ----------
    username: str
        name of the TissueMAPS user

    Returns
    -------
    str
        password for the given user

    '''
    message = 'Enter password for user "{0}": '.format(username)
    password = getpass.getpass(message)
    if not password:
        raise ValueError(
            'No credentials provided for user "{0}"'.format(username)
        )
    return password
