# Copyright 2016-2019 University of Zurich
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
import atexit
import base64
import cgi
import errno
from functools import partial
import glob
import inspect
import json
import logging
import os
import re
import shutil
import sys
from io import BytesIO
try:
    # NOTE: Python3 no longer has the cStringIO module
    from cStringIO import StringIO
except ImportError:
    from io import StringIO
from subprocess import check_call, check_output, CalledProcessError
import tempfile

import cv2
from prettytable import PrettyTable
import numpy as np
import pandas as pd
from pandas.io.common import EmptyDataError
import requests
import yaml

from tmclient.base import HttpClient
from tmclient.log import configure_logging
from tmclient.log import map_logging_verbosity
from tmclient.errors import ResourceError
from tmclient.auth import prompt_for_credentials, load_credentials_from_file


logger = logging.getLogger(__name__)


# The `SUPPORTED_IMAGE_FORMATS` dictionary serves two purposes:
#
# 1. Keys are file extensions (starting with a dot, as returned by
#    `os.path.splitext`) that are recognized as image files (and
#    thus converted upon request)
#
# 2. Values are the corresponding "delegate" name that must be present
#    in the output of `convert --version` in order to be sure that
#    ImageMagick's `convert` can actually handle that format. (For
#    instance: it is possible, though unlikely, that ImageMagick is
#    compiled with PNG support.)
#
SUPPORTED_IMAGE_FORMATS = {
    # extension ==> ImageMagick "delegate" name
    '.tif'  : 'tiff',
    '.tiff' : 'tiff',
    '.jpg'  : 'jpeg',
    '.jpeg' : 'jpeg',
    '.png'  : 'png',
}


def replace_ext(filename, ext):
    """
    Return new pathname formed by replacing extension in `filename` with `ext`.
    """
    if ext.startswith('.'):
        ext = ext[1:]
    stem, _ = os.path.splitext(filename)
    return (stem + '.' + ext)


def check_imagemagick_supported_format(fmt):
    """
    Return ``True`` if `convert` can be run and reports supporting image format `fmt`.
    """
    try:
        convert_output = check_output(['convert', '--version'])
    # `subprocess` raises `OSError` if the executable is not found
    except (CalledProcessError, OSError) as err:
        logger.error(
            "Cannot run ImageMgick's `convert` program."
            " On Debian/Ubuntu, use `sudo apt-get install imagemagick`"
            " to install it.")
        return False
    # example `convert --version` output::
    #
    #     $ convert --version
    #     Version: ImageMagick 6.9.7-4 Q16 x86_64 20170114 http://www.imagemagick.org
    #     Copyright: (c) 1999-2017 ImageMagick Studio LLC
    #     License: http://www.imagemagick.org/script/license.php
    #     Features: Cipher DPC Modules OpenMP
    #     Delegates (built-in): bzlib djvu fftw fontconfig freetype jbig jng jpeg lcms lqr ltdl lzma openexr pangocairo png tiff wmf x xml zlib
    #
    # the following loop will make it such that::
    #
    #     supported = ['bzlib', 'djvu', ...]
    #
    supported = []
    for line in convert_output.split('\n'):
        line = line.lower()
        if line.startswith('delegates'):
            supported += line.split(':', 1)[1].split()
    # allow fmt to be ``png``, ``JPEG``, ``.TIF`` etc.
    fmt = fmt.lower()
    if not fmt.startswith('.'):
        fmt = '.' + fmt
    try:
        delegate = SUPPORTED_IMAGE_FORMATS[fmt]
    except KeyError:
        logger.error("Image format `%s` not supported by `tm_client`.")
        return False
    if delegate in supported:
        return True
    else:
        logger.error("Image format `%s` not in ImageMagick's `convert` delegates.")
        return False


class TmClient(HttpClient):

    '''*TissueMAPS* RESTful API client.'''

    def __init__(self, host, port, username, password,
            experiment_name=None, ca_bundle=None):
        '''
        Parameters
        ----------
        host: str
            name or IP address of the machine that hosts the *TissueMAPS* server
            (e.g. ``"localhost"``, ``127.0.0.1`` or ``app.tissuemaps.org``)
        port: int
            number of the port to which server listens
            (e.g. ``80``, ``443`` or ``8002``)
        username: str
            name of the *TissueMAPS* user
        password: str
            password for the user (can also be provided via the
            *tm_pass* file)
        experiment_name: str, optional
            name of the experiment that should be accessed
        ca_bundle: str, optional
            path to a CA bundle file in Privacy Enhanced Mail (PEM) format

        Examples
        --------
        # Access general resources
        >>>client = TmClient('localhost', 8002, 'devuser', '123456')
        >>>client.get_experiments()

        # Access experiment-specific resources, exemplied for an experiment
        # called "test".
        # The name of the experiment can be provided via the constructor:
        >>>client = TmClient('localhost', 8002, 'devuser', '123456', 'test')
        >>>client.get_plates()
        # Alternatively, it can be set separately:
        >>>client = TmClient('localhost', 8002, 'devuser', '123456')
        >>>client.experiment_name = 'test'
        >>>client.get_plates()
        '''
        super(TmClient, self).__init__(host, port, username, password, ca_bundle)
        self.experiment_name = experiment_name

    @property
    def experiment_name(self):
        '''str: name of the currently accessed experiment'''
        if self._experiment_name is None:
            logger.error('experiment name is not set')
            raise AttributeError('Attribute experiment_name is not set.')
        return self._experiment_name

    @experiment_name.setter
    def experiment_name(self, value):
        self._experiment_name = str(value)

    def get_experiments(self):
        '''Gets information for all experiments.

        Returns
        -------
        List[Dict[str, str]]
            id, name and description for each experiment

        See also
        --------
        :func:`tmserver.api.experiment.get_experiments`
        :class:`tmlib.models.experiment.Experiment`
        '''
        logger.info('get experiments')
        url = self._build_api_url('/experiments')
        res = self._session.get(url)
        res.raise_for_status()
        return res.json()['data']

    def _list_experiments(self):
        experiments = self.get_experiments()
        t = PrettyTable(['ID', 'Name', 'Description'])
        t.align['Name'] = 'l'
        t.align['Description'] = 'l'
        t.padding_width = 1
        for e in experiments:
            t.add_row([e['id'], e['name'], e['description']])
        print(t)

    def __call__(self, cli_args):
        '''Calls a method with the provided arguments.

        Paramaters
        ----------
        cli_args: argparse.Namespace
            parsed command line arguments that should be passed on to the
            specified method (appropriate arguments get automatically stripped)

        Raises
        ------
        AttributeError
            when `cli_args` don't have an attribute "method" that specifies
            the method that should be called or when the class doesn't have the
            specied method
        '''
        if not hasattr(cli_args, 'method'):
            raise AttributeError('Parser must specify "method".')
        method_name = cli_args.method
        logger.debug('call method "%s"', method_name)
        if not hasattr(self, method_name):
            raise AttributeError(
                'Object of type "{0}" doesn\'t have a method "{1}"'.format(
                    self.__class__.__name__, method_name
                )
            )
        args = vars(cli_args)
        method = getattr(self, method_name)
        kwargs = dict()
        valid_arg_names = inspect.getargspec(method).args
        for arg_name, arg_value in args.items():
            if arg_name in valid_arg_names:
                kwargs[arg_name] = arg_value
        method(**kwargs)

    @classmethod
    def __main__(cls):
        '''Main entry point for command line interface.'''
        from tmclient.cli import parser
        args = parser.parse_args()

        configure_logging()
        logging_level = map_logging_verbosity(args.verbosity)
        logging.getLogger('tmclient').setLevel(logging_level)
        logger.setLevel(logging_level)

        if not args.username:
            logger.error(
                "Please give a user name,"
                " either via the `--user` command-line option,"
                " or by setting the `TM_USER` environment variable.")
            sys.exit(os.EX_USAGE)

        try:
            args.port = int(args.port)
        except (ValueError, TypeError):
            logger.error(
                "Invalid value for server port: `%s`;"
                " it should be an integer number in the range 1..65535."
                " Plase set it either via the `--port` command-line option,"
                " or by setting the `TM_PORT` environment variable.")
            sys.exit(os.EX_USAGE)

        if not args.password:
            try:
                args.password = load_credentials_from_file(args.username)
            except (RuntimeError, KeyError):
                args.password = prompt_for_credentials(args.username)

        try:
            client = cls(
                args.host, args.port, args.username, args.password
            )
            try:
                client.experiment_name = args.experiment_name
            except AttributeError:
                pass  # no `args.experiment_name`
            client(args)
        except Exception as err:
            if args.verbosity < 4:
                logger.error(str(err))
                sys.exit(1)
            else:
                raise

    def _build_api_url(self, route, params={}):
        if not route.startswith('/'):
            route = '/api/' + route
        else:
            route = '/api' + route
        return super(TmClient, self)._build_url(route, params)

    @property
    def _experiment_id(self):
        if not hasattr(self, '_TmClient__experiment_id'):
            logger.debug('get ID for experiment "%s"', self.experiment_name)
            params = {'name': self.experiment_name}
            url = self._build_api_url('/experiments', params)
            res = self._session.get(url)
            res.raise_for_status()
            data = res.json()['data']
            if len(data) > 1:
                raise ResourceError(
                    'More than one experiment found with name "{0}"'.format(
                        self.experiment_name
                    )
                )
            if len(data) == 0:
                raise ResourceError(
                    'No experiment found with name "{0}"'.format(
                        self.experiment_name
                    )
                )
            self.__experiment_id = data[0]['id']
        return self.__experiment_id

    @_experiment_id.setter
    def _experiment_id(self, value):
        self.__experiment_id = value

    def create_experiment(self, workflow_type, microscope_type, plate_format,
            plate_acquisition_mode):
        '''Creates the experiment.

        Parameters
        ----------
        workflow_type: str
            workflow type
        microscope_type: str
            microscope type
        plate_format: int
            well-plate format, i.e. total number of wells per plate
        plate_acquisition_mode: str
            mode of image acquisition that determines whether acquisitions will
            be interpreted as time points as part of a time series experiment
            or as multiplexing cycles as part of a serial multiplexing
            experiment

        Returns
        -------
        dict
            experiment resource representation

        See also
        --------
        :func:`tmserver.api.experiment.create_experiment`
        :class:`tmlib.models.experiment.ExperimentReference`
        :class:`tmlib.models.experiment.Experiment`
        '''
        logger.info('create experiment "%s"', self.experiment_name)
        content = {
            'name': self.experiment_name,
            'workflow_type': workflow_type,
            'microscope_type': microscope_type,
            'plate_format': plate_format,
            'plate_acquisition_mode': plate_acquisition_mode
        }
        url = self._build_api_url('/experiments')
        res = self._session.post(url, json=content)
        res.raise_for_status()
        data = res.json()['data']
        self._experiment_id = data['id']
        return data

    def rename_experiment(self, new_name):
        '''Renames the experiment.

        Parameters
        ----------

        See also
        --------
        :func:`tmserver.api.experiment.update_experiment`
        :class:`tmlib.models.experiment.ExperimentReference`
        '''
        logger.info('rename experiment "%s"', self.experiment_name)
        content = {'name': new_name}
        url = self._build_api_url(
            '/experiments/{experiment_id}'.format(
                experiment_id=self._experiment_id
            )
        )
        res = self._session.put(url, json=content)
        res.raise_for_status()
        self.experiment_name = new_name

    def delete_experiment(self):
        '''Deletes the experiment.

        See also
        --------
        :func:`tmserver.api.experiment.delete_experiment`
        :class:`tmlib.models.experiment.ExperimentReference`
        :class:`tmlib.models.experiment.Experiment`
        '''
        logger.info('delete experiment "%s"', self.experiment_name)
        url = self._build_api_url(
            '/experiments/{experiment_id}'.format(
                experiment_id=self._experiment_id
            )
        )
        res = self._session.delete(url)
        res.raise_for_status()
        del self.__experiment_id

    def _get_plate_id(self, name):
        logger.debug(
            'get plate ID for experiment "%s", plate "%s"',
            self.experiment_name, name
        )
        params = {
            'name': name,
        }
        url = self._build_api_url(
            '/experiments/{experiment_id}/plates'.format(
                experiment_id=self._experiment_id
            ),
            params
        )
        res = self._session.get(url)
        res.raise_for_status()
        data = res.json()['data']
        if len(data) > 1:
            raise ResourceError(
                'More than one plate found with name "{0}"'.format(name)
            )
        elif len(data) == 0:
            raise ResourceError(
                'No plate found with name "{0}"'.format(name)
            )
        return data[0]['id']

    def create_plate(self, name, description=''):
        '''Creates a new plate.

        Parameters
        ----------
        name: str
            name that should be given to the plate
        description: str, optional
            description of the plate

        Returns
        -------
        dict
            plate resource representation

        See also
        --------
        :func:`tmserver.api.plate.create_plate`
        :class:`tmlib.models.plate.Plate`
        '''
        logger.info(
            'create plate "%s" for experiment "%s"',
            name, self.experiment_name
        )
        content = {
            'name': name,
            'description': description
        }
        url = self._build_api_url(
            '/experiments/{experiment_id}/plates'.format(
                experiment_id=self._experiment_id
            )
        )
        res = self._session.post(url, json=content)
        res.raise_for_status()
        return res.json()['data']

    def delete_plate(self, name):
        '''Deletes a plate.

        Parameters
        ----------
        name: str
            name of the plate that should be deleted

        See also
        --------
        :func:`tmserver.api.plate.delete_plate`
        :class:`tmlib.models.plate.Plate`
        '''
        logger.info(
            'delete plate "%s" of experiment "%s"',
            name, self.experiment_name
        )
        plate_id = self._get_plate_id(name)
        url = self._build_api_url(
            '/experiments/{experiment_id}/plates/{plate_id}'.format(
                experiment_id=self._experiment_id, plate_id=plate_id
            )
        )
        res = self._session.delete(url)
        res.raise_for_status()

    def rename_plate(self, name, new_name):
        '''Renames a plate.

        Parameters
        ----------
        name: str
            name of the plate that should be renamed
        new_name: str
            name that should be given to the plate

        See also
        --------
        :func:`tmserver.api.plate.update_plate`
        :class:`tmlib.models.plate.Plate`
        '''
        logger.info(
            'rename plate "%s" of experiment "%s"',
            name, self.experiment_name
        )
        plate_id = self._get_plate_id(name)
        content = {'name': new_name}
        url = self._build_api_url(
            '/experiments/{experiment_id}/plates/{plate_id}'.format(
                experiment_id=self._experiment_id, plate_id=plate_id
            )
        )
        res = self._session.put(url, json=content)
        res.raise_for_status()

    def get_plates(self):
        '''Gets information about plates.

        Returns
        -------
        List[Dict[str, str]]
            id, name, status and description for each plate

        See also
        --------
        :func:`tmserver.api.plate.get_plates`
        :class:`tmlib.models.plate.Plate`
        '''
        logger.info('get plates of experiment "%s"', self.experiment_name)
        url = self._build_api_url(
            '/experiments/{experiment_id}/plates'.format(
                experiment_id=self._experiment_id
            )
        )
        res = self._session.get(url)
        res.raise_for_status()
        return res.json()['data']

    def _list_plates(self):
        plates = self.get_plates()
        t = PrettyTable(['ID', 'Status', 'Name', 'Description'])
        t.align['Name'] = 'l'
        t.align['Description'] = 'l'
        t.padding_width = 1
        for p in plates:
            t.add_row([p['id'], p['status'], p['name'], p['description']])
        print(t)

    def _get_acquisition_id(self, plate_name, name):
        logger.debug(
            'get acquisition ID for experiment "%s", plate "%s" and '
            'acquisition "%s"',
            self.experiment_name, plate_name, name
        )
        params = {
            'plate_name': plate_name,
            'name': name
        }
        url = self._build_api_url(
            '/experiments/{experiment_id}/acquisitions'.format(
                experiment_id=self._experiment_id
            ),
            params
        )
        res = self._session.get(url)
        res.raise_for_status()
        data = res.json()['data']
        if len(data) > 1:
            raise ResourceError(
                'More than one acquisition found with name "{0}" for '
                'plate "{1}"'.format(name, plate_name)
            )
        elif len(data) == 0:
            raise ResourceError(
                'No acquisition found with name "{0}" for '
                'plate "{1}"'.format(name, plate_name)
            )
        return data[0]['id']

    def create_acquisition(self, plate_name, name, description=''):
        '''Creates a new acquisition.

        Parameters
        ----------
        plate_name: str
            name of the parent plate
        name: str
            name that should be given to the acquisition
        description: str, optional
            description of the acquisition

        Returns
        -------
        dict
            acquisition resource representation

        See also
        --------
        :func:`tmserver.api.acquisition.create_acquisition`
        :class:`tmlib.models.acquisition.Acquisition`
        '''
        logger.info(
            'create acquisition "%s" for plate "%s" of experiment "%s"',
            name, plate_name, self.experiment_name
        )
        content = {
            'plate_name': plate_name,
            'name': name,
            'description': description
        }
        url = self._build_api_url(
            '/experiments/{experiment_id}/acquisitions'.format(
                experiment_id=self._experiment_id
            )
        )
        res = self._session.post(url, json=content)
        res.raise_for_status()
        return res.json()['data']

    def rename_acquisition(self, plate_name, name, new_name):
        '''Renames an acquisition.

        Parameters
        ----------
        plate_name: str
            name of the parent plate
        name: str
            name of the acquisition that should be renamed
        new_name: str
            name that should be given to the acquisition

        See also
        --------
        :func:`tmserver.api.acquisition.update_acquisition`
        :class:`tmlib.models.acquisition.Acquisition`
        '''
        logger.info(
            'rename acquisistion "%s" of experiment "%s", plate "%s"',
            name, self.experiment_name, plate_name
        )
        content = {'name': new_name}
        acquisition_id = self._get_acquisition_id(plate_name, name)
        url = self._build_api_url(
            '/experiments/{experiment_id}/acquisitions/{acquisition_id}'.format(
                experiment_id=self._experiment_id, acquisition_id=acquisition_id
            )
        )
        res = self._session.put(url, json=content)
        res.raise_for_status()

    def delete_acquisition(self, plate_name, name):
        '''Deletes an acquisition.

        Parameters
        ----------
        plate_name: str
            name of the parent plate
        name: str
            name of the acquisition that should be deleted

        See also
        --------
        :func:`tmserver.api.acquisition.delete_acquisition`
        :class:`tmlib.models.acquisition.Acquisition`
        '''
        logger.info(
            'delete acquisition "%s" of experiment "%s", plate "%s"',
            name, self.experiment_name, plate_name
        )
        acquisition_id = self._get_acquisition_id(plate_name, name)
        url = self._build_api_url(
            '/experiments/{experiment_id}/acquisitions/{acquisition_id}'.format(
                experiment_id=self._experiment_id, acquisition_id=acquisition_id
            )
        )
        res = self._session.delete(url)
        res.raise_for_status()

    def get_acquisitions(self, plate_name=None):
        '''Gets information about acquisitions.

        Parameters
        ----------
        plate_name: str, optional
            name of the parent plate for which acquisitions should be filtered

        Returns
        -------
        List[Dict[str, str]]
            id, name, status, description and plate_name for each acquisition

        See also
        --------
        :func:`tmserver.api.acquisition.get_acquisitions`
        :class:`tmlib.models.acquisition.Acquisition`
        '''
        logger.info('get acquisitions of experiment "%s"', self.experiment_name)
        params = dict()
        if plate_name is not None:
            logger.info('filter acquisitions for plate "%s"', plate_name)
            params['plate_name'] = plate_name
        url = self._build_api_url(
            '/experiments/{experiment_id}/acquisitions'.format(
                experiment_id=self._experiment_id
            ),
            params
        )
        res = self._session.get(url)
        res.raise_for_status()
        return res.json()['data']

    def _list_acquisitions(self, plate_name=None):
        acquisitions = self.get_acquisitions(plate_name)
        t = PrettyTable(['ID', 'Status', 'Name', 'Description', 'Plate'])
        t.padding_width = 1
        for a in acquisitions:
            t.add_row([
                a['id'], a['status'], a['name'], a['description'],
                a['plate_name']
        ])
        print(t)

    def _get_well_id(self, plate_name, name):
        logger.debug(
            'get well ID for experiment "%s", plate "%s" and well "%s"',
            self.experiment_name, plate_name, name
        )
        params = {
            'plate_name': plate_name,
            'name': name
        }
        url = self._build_api_url(
            '/experiments/{experiment_id}/wells'.format(
                experiment_id=self._experiment_id
            ),
            params
        )
        res = self._session.get(url)
        res.raise_for_status()
        data = res.json()['data']
        if len(data) > 1:
            raise ResourceError(
                'More than one well found with name "{0}" for '
                'plate "{1}"'.format(name, plate_name)
            )
        elif len(data) == 0:
            raise ResourceError(
                'No well found with name "{0}" for plate "{1}"'.format(
                    name, plate_name
                )
            )
        return data[0]['id']

    def get_wells(self, plate_name=None):
        '''Gets information about wells.

        Parameters
        ----------
        plate_name: str, optional
            name of the parent plate

        Returns
        -------
        List[Dict[str, str]]
            id, name and description of each well

        See also
        --------
        :func:`tmserver.api.well.get_wells`
        :class:`tmlib.models.well.Well`
        '''
        logger.info('get wells of experiment "%s"', self.experiment_name)
        params = dict()
        if plate_name is not None:
            logger.info('filter wells for plate "%s"', plate_name)
            params['plate_name'] = plate_name
        url = self._build_api_url(
            '/experiments/{experiment_id}/wells'.format(
                experiment_id=self._experiment_id
            ),
            params
        )
        res = self._session.get(url)
        res.raise_for_status()
        return res.json()['data']

    def _list_wells(self, plate_name=None):
        wells = self.get_wells(plate_name)
        t = PrettyTable(['ID', 'Name', 'Description', 'Plate'])
        t.align['Description'] = 'l'
        t.padding_width = 1
        for w in wells:
            t.add_row([w['id'], w['name'], w['description'], w['plate']])
        print(t)

    def _get_site_id(self, plate_name, well_name, well_pos_y, well_pos_x):
        logger.debug(
            'get site ID for experiment "%s", plate "%s", well "%s", y %d, x %d',
            self.experiment_name, plate_name, well_name, well_pos_y, well_pos_x
        )
        params = {
            'plate_name': plate_name,
            'well_name': name,
            'well_pos_y': well_pos_y,
            'well_pos_x': well_pos_x
        }
        url = self._build_api_url(
            '/experiments/{experiment_id}/sites'.format(
                experiment_id=self._experiment_id
            ),
            params
        )
        res = self._session.get(url)
        res.raise_for_status()
        data = res.json()['data']
        if len(data) > 1:
            raise ResourceError(
                'More than one site found at y %d, x %d for well "{0}" and '
                'plate "{1}"'.format(
                    well_pos_y, well_pos_x, well_name, plate_name
                )
            )
        elif len(data) == 0:
            raise ResourceError(
                'No site found at y %d, x %d for well "{0}" and '
                'plate "{1}"'.format(
                    well_pos_y, well_pos_x, well_name, plate_name
                )
            )
        return data[0]['id']

    def get_sites(self, plate_name=None, well_name=None):
        '''Gets information about sites.

        Parameters
        ----------
        plate_name: str, optional
            name of the parent plate for which sites should be filtered
        well_name: str, optional
            name of the parent well for which sites should be filtered

        Returns
        -------
        List[Dict[str, str]]
            id, name and description of each well

        See also
        --------
        :func:`tmserver.api.well.get_wells`
        :class:`tmlib.models.well.Well`
        '''
        logger.info('get sites of experiment "%s"', self.experiment_name)
        params = dict()
        if plate_name is not None:
            logger.info('filter sites for plate "%s"', plate_name)
            params['plate_name'] = plate_name
        if well_name is not None:
            logger.info('filter sites for well "%s"', well_name)
            params['well_name'] = well_name
        url = self._build_api_url(
            '/experiments/{experiment_id}/sites'.format(
                experiment_id=self._experiment_id
            ),
            params
        )
        res = self._session.get(url)
        res.raise_for_status()
        return res.json()['data']

    def _list_sites(self, plate_name=None, well_name=None):
        sites = self.get_sites(plate_name)
        t = PrettyTable(['ID', 'Y', 'X', 'Height', 'Width', 'Well', 'Plate'])
        t.padding_width = 1
        for s in sites:
            t.add_row([
                s['id'], s['y'], s['x'], s['height'], s['width'],
                s['well_name'], s['plate_name']
            ])
        print(t)

    def _get_mapobject_type_id(self, name):
        logger.debug(
            'get mapobject type ID for experiment "%s" and mapobjec type "%s"',
            self.experiment_name, name
        )
        params = {'name': name}
        url = self._build_api_url(
            '/experiments/{experiment_id}/mapobject_types'.format(
                experiment_id=self._experiment_id
            ),
            params
        )
        res = self._session.get(url)
        res.raise_for_status()
        data = res.json()['data']
        if len(data) > 1:
            raise ResourceError(
               'More than one mapobject type found with name "{0}"'.format(
                    name
                )
            )
        elif len(data) == 0:
            raise ResourceError(
               'No mapobject type found with name "{0}"'.format(name)
            )
        return data[0]['id']

    def _get_feature_id(self, mapobject_type_name, name):
        logger.debug(
            'get feature ID for experiment "%s", mapobject type "%s" '
            'and feature "%s"', self.experiment_name, mapobject_type_name, name
        )
        params = {'name': name}
        mapobject_type_id = self._get_mapobject_type_id(mapobject_type_name)
        url = self._build_api_url(
            '/experiments/{experiment_id}/mapobject_types/{mapobject_type_id}/features'.format(
                experiment_id=self._experiment_id,
                mapobject_type_id=mapobject_type_id
            ),
            params
        )
        res = self._session.get(url)
        res.raise_for_status()
        data = res.json()['data']
        if len(data) > 1:
            raise ResourceError(
                'More than one feature found with name "{0}"'.format(name)
            )
        elif len(data) == 0:
            raise ResourceError(
                'No feature found with name "{0}"'.format(name)
            )
        return data[0]['id']

    def _get_cycle_id(self, plate_name, index):
        logger.debug(
            'get cycle ID for experiment "%s", plate "%s" and cycle #%d',
            self.experiment_name, plate_name, index
        )
        params = {
            'plate_name': plate_name,
            'index': index
        }
        url = self._build_api_url(
            '/experiments/{experiment_id}/cycles'.format(
                experiment_id=self._experiment_id
            ),
            params
        )
        res = self._session.get(url)
        res.raise_for_status()
        data = res.json()['data']
        if len(data) > 1:
            raise ResourceError(
                'More than one cycle found for index {0} and plate "{1}"'.format(
                    index, plate_name
                )
            )
        elif len(data) == 0:
            raise ResourceError(
                'No cycle found for index {0} and plate "{1}"'.format(
                    cycle_index, plate_name
                )
            )
        return data[0]['id']

    def _get_channel_id(self, name):
        logger.debug(
            'get channel ID for experiment "%s" and channel "%s"',
            self.experiment_name, name
        )
        params = {'name': name}
        url = self._build_api_url(
            '/experiments/{experiment_id}/channels'.format(
                experiment_id=self._experiment_id
            ),
            params
        )
        res = self._session.get(url)
        res.raise_for_status()
        data = res.json()['data']
        if len(data) > 1:
            raise ResourceError(
                'More than one channel found with name "{0}"'.format(name)
            )
        elif len(data) == 0:
            raise ResourceError(
                'No channel found with name "{0}"'.format(name)
            )
        return data[0]['id']

    def _get_channel_layer_id(self, channel_name, tpoint, zplane):
        logger.debug(
            'get channel layer ID for experiment "%s", channel "%s", tpoint %d '
            'and zplane %d', self.experiment_name, channel_name, tpoint, zplane
        )
        params = {
            'channel_name': channel_name,
            'tpoint': tpoint,
            'zplane': zplane
        }
        url = self._build_api_url(
            '/experiments/{experiment_id}/channel_layers'.format(
                experiment_id=self._experiment_id
            ),
            params
        )
        res = self._session.get(url)
        res.raise_for_status()
        data = res.json()['data']
        if len(data) > 1:
            raise ResourceError(
                'More than one channel layer found for experiment "{0}", '
                'channel "{1}", tpoint {2} and zplane {3}'.format(
                    self.experiment_name, channel_name, tpoint, zplane
                )
            )
        elif len(data) == 0:
            raise ResourceError(
                'No channel layer found for experiment "{0}", channel "{1}", '
                'tpoint {2} and zplane {3}'.format(
                    experiment_name, channel_name, tpoint, zplane
                )
            )
        return data[0]['id']

    def get_microscope_files(self, plate_name, acquisition_name):
        '''Gets status and name of files that have been registered for upload.

        Parameters
        ----------
        plate_name: str
            name of the parent plate
        acquisition_name: str
            name of the parent acquisition

        Returns
        -------
        List[Dict[str, str]]
            names and status of uploaded files

        See also
        --------
        :func:`tmserver.api.acquisition.get_microscope_image_files_information`
        :func:`tmserver.api.acquisition.get_microscope_metadata_file_information`
        :class:`tmlib.models.acquisition.Acquisition`
        :class:`tmlib.models.file.MicroscopeImageFile`
        :class:`tmlib.models.file.MicroscopeMetadataFile`
        '''
        logger.info(
            'get names of already uploaded files for experiment "%s", '
            'plate "%s" and acquisition "%s"', self.experiment_name, plate_name,
            acquisition_name
        )
        acquisition_id = self._get_acquisition_id(plate_name, acquisition_name)
        image_files = self._get_image_files(acquisition_id)
        metadata_files = self._get_metadata_files(acquisition_id)
        return image_files + metadata_files

    def _list_microscope_files(self, plate_name, acquisition_name):
        files = self.get_microscope_files(plate_name, acquisition_name)
        t = PrettyTable(['ID', 'Status', 'Name'])
        t.align['Name'] = 'l'
        t.padding_width = 1
        for f in files:
            t.add_row([f['id'], f['status'], f['name']])
        print(t)

    def _get_image_files(self, acquisition_id):
        logger.debug('get image files for acquisition %s', acquisition_id)
        url = self._build_api_url(
            '/experiments/{experiment_id}/acquisitions/{acquisition_id}/images'.format(
                experiment_id=self._experiment_id, acquisition_id=acquisition_id
            )
        )
        res = self._session.get(url)
        res.raise_for_status()
        return res.json()['data']

    def _get_metadata_files(self, acquisition_id):
        logger.debug(
            'get metadata files for experiment "%s" and acquisition %s',
            self.experiment_name, acquisition_id
        )
        url = self._build_api_url(
            '/experiments/{experiment_id}/acquisitions/{acquisition_id}/metadata'.format(
                experiment_id=self._experiment_id, acquisition_id=acquisition_id
            )
        )
        res = self._session.get(url)
        res.raise_for_status()
        return res.json()['data']

    def upload_microscope_files(self, plate_name, acquisition_name,
                                path, parallel=1, retry=5,
                                convert=None, delete_after_upload=False,
                                _deprecated_directory_option=False):
        '''
        Uploads microscope files contained in `path`.
        If `path` is a directory, upload all files contained in it.

        Parameters
        ----------
        plate_name: str
            name of the parent plate
        acquisition_name: str
            name of the parent acquisition
        path: str
            path to a directory on disk where the files that should be uploaded
            are located
        parallel: int
            number of parallel processes to use for upload
        retry: int
            number of times to retry failed uploads
        convert: str
            Format to convert images to during the upload process.
            Given as a string specifying the new file extension (e.g.,
            ``png`` or ``jpg``).  If ``None`` or the empty string,
            no conversion takes place and files are uploaded as-is.
        delete_after_upload: bool
            Delete source files after successful upload.

        Returns
        -------
        List[str]
            names of registered files

        See also
        --------
        :func:`tmserver.api.acquisition.add_microscope_file`
        :class:`tmlib.models.file.MicroscopeImageFile`
        :class:`tmlib.models.file.MicroscopeMetadataFile`
        '''
        if _deprecated_directory_option:
            logger.warn(
                "The `--directory` option is now superfluous."
                " You can remove it from the command line.")
        # TODO: consider using os.walk() to screen subdirectories recursively
        logger.info(
            'upload microscope files for experiment "%s", plate "%s" '
            'and acquisition "%s"',
            self.experiment_name, plate_name, acquisition_name
        )
        if convert:
            # FIXME: This checks that `convert` can handle the
            # *destination* image format, but it could be lacking
            # support for the *source* image format... But the source
            # images are many and, in principle, they could be of many
            # different formats...
            if not check_imagemagick_supported_format(convert):
                logger.fatal(
                    "Aborting: conversion requested"
                    " but ImageMagick's `convert` not available.")
                return -1
            logger.info("files will be converted to %s format", convert)
        acquisition_id = self._get_acquisition_id(plate_name, acquisition_name)

        path = os.path.expandvars(os.path.expanduser(path))
        if os.path.isdir(path):
            filenames = [
                f for f in os.listdir(path)
                if (not f.startswith('.')
                    and not os.path.isdir(os.path.join(path, f)))
            ]
            paths = [
                os.path.join(path, name) for name in filenames
            ]
        else:
            filenames = [ os.path.basename(path) ]
            paths = [ path ]
        if convert:
            filenames_to_register = []
            for filename in filenames:
                # note: `ext` starts with a dot!
                name, ext = os.path.splitext(filename)
                if ext in SUPPORTED_IMAGE_FORMATS:
                    filenames_to_register.append(replace_ext(filename, convert))
                else:
                    # no image, no change
                    filenames_to_register.append(filename)
        else:
            filenames_to_register = filenames
        registered_filenames = self._register_files_for_upload(
            acquisition_id, filenames_to_register
        )
        logger.info('registered %d files', len(registered_filenames))

        if convert:
            # make temporary directory and schedule its deletion
            convert_dir = tempfile.mkdtemp(prefix='tm_client', suffix='.d')
            atexit.register(shutil.rmtree, convert_dir, ignore_errors=True)
        else:
            convert_dir = None  # unused, but still have to provide it

        upload_url = self._build_api_url(
            '/experiments/{experiment_id}/acquisitions/{acquisition_id}/microscope-file'
            .format(experiment_id=self._experiment_id, acquisition_id=acquisition_id)
        )
        total = len(paths)
        retry += 1  # make usage here consistent with CLI usage
        while retry > 0:
            work = [
                # function,         *args ...
                (self._upload_file, upload_url, path, convert,
                                    delete_after_upload, convert_dir)
                for path in paths
            ]
            outcome = self._parallelize(work, parallel)
            # report on failures
            paths = [path for (ok, path) in outcome if not ok]
            failed = len(paths)
            successful = total - failed
            logger.info('file uploads: %d successful, %d failed', successful, failed)
            # try again?
            if failed == 0:
                break
            else:
                retry -= 1
                total = failed
                logger.info('trying again to upload failed files ...')

        return registered_filenames



    def register_microscope_files(self,
                                  plate_name, acquisition_name, path):
        '''
        Register microscope files contained in `path` (Server side).

        Parameters
        ----------
        plate_name: str
            name of the parent plate
        acquisition_name: str
            name of the parent acquisition
        path: str
            path to a directory on disk where the files that should be uploaded
            are located
        Returns:
        -------
        List[str]
            names of registered files
        '''

        logger.info(
            'register directory `%s` for experiment "%s",'
            ' plate "%s" and acquisition "%s"',
            path, self.experiment_name, plate_name, acquisition_name
        )

        acquisition_id = self._get_acquisition_id(plate_name, acquisition_name)
        register_url = self._build_api_url(
            '/experiments/{experiment_id}/acquisitions/{acquisition_id}/register'
            .format(experiment_id=self._experiment_id, acquisition_id=acquisition_id)
        )

        logger.debug('register files for upload')
        url = self._build_api_url('/experiments/{experiment_id}/acquisitions/{acquisition_id}/register'.format(experiment_id=self._experiment_id, acquisition_id=acquisition_id))
        payload = {'path': path}
        res = self._session.post(url, json=payload)
        res.raise_for_status()
        return res.json()['message']


    def _register_files_for_upload(self, acquisition_id, filenames):
        logger.debug('register files for upload')
        url = self._build_api_url(
            '/experiments/{experiment_id}/acquisitions/{acquisition_id}/upload/register'.format(
                experiment_id=self._experiment_id, acquisition_id=acquisition_id
            )
        )
        payload = {'files': filenames}
        res = self._session.post(url, json=payload)
        res.raise_for_status()
        return res.json()['data']

    def _upload_file(self, upload_url, filepath,
                     convert=None, delete=False, convert_dir=None):
        if convert_dir is None:
            # make temporary directory and schedule its deletion
            convert_dir = tempfile.mkdtemp(prefix='tm_client', suffix='.d')
            atexit.register(shutil.rmtree, convert_dir, ignore_errors=True)
        # note: `ext` starts with a dot!
        _, ext = os.path.splitext(filepath)
        if convert and ext in SUPPORTED_IMAGE_FORMATS:
            file_to_upload = os.path.join(
                convert_dir,
                replace_ext(os.path.basename(filepath), convert))
            logger.debug(
                'converting source file `%s` to `%s` (%s format) ...',
                filepath, file_to_upload, convert)
            check_call(
                ['convert', filepath, '-depth', '16',
                 '-colorspace', 'gray', file_to_upload])
        else:
            file_to_upload = filepath
        logger.debug('uploading file `%s` ...', file_to_upload)
        with open(file_to_upload, 'rb') as stream:
            files = {'file': stream}
            res = self._session.post(upload_url, files=files)
        if convert and (filepath != file_to_upload):
            try:
                os.remove(file_to_upload)
            except Exception as err:
                logger.warn(
                    "Cannot delete temporary file `%s`: %s",
                    file_to_upload, err)
        if res.ok:
            logger.debug(
                'successfully uploaded file `%s`, elapsed %.3fs',
                filepath, res.elapsed.total_seconds())
            if delete:
                try:
                    os.remove(filepath)
                    logger.debug(
                        "deleted successfully uploaded file `%s`",
                        filepath)
                except Exception as err:
                    logger.warn("Could not remove file `%s`: %s",
                                filepath, err)
            return (True, filepath)
        else:
            logger.error('upload of file `%s` failed: %d %s',
                          filepath, res.status_code, res.reason)
            if __debug__:
                logger.debug('=== Response data follows ===')
                for k, v in res.headers.iteritems():
                    logger.debug('%s: %s', k, v)
                logger.debug('--- body ---')
                for line in res.text.split('\n'):
                    logger.debug(line)
                logger.debug('=== Response data ends ===')
            return (False, filepath)

    @classmethod
    def _extract_filename_from_headers(cls, headers):
        value, params = cgi.parse_header(headers.get('Content-Disposition'))
        try:
            return params['filename']
        except KeyError:
            raise Exception(
                'No filename found in header field "Content-Disposition".'
            )

    @classmethod
    def _write_file(cls, directory, filename, data):
        directory = os.path.expanduser(directory)
        directory = os.path.expandvars(directory)
        if not os.path.exists(directory):
            raise OSError('Download directory does not exist: %s', directory)
        filepath = os.path.join(directory, filename)
        logger.info('write file: %s', filepath)
        with open(filepath, 'wb') as f:
            f.write(data)

    def _download_channel_image(self, channel_name, plate_name,
            well_name, well_pos_y, well_pos_x,
            cycle_index=0, tpoint=0, zplane=0, correct=True, align = False):
        logger.info(
            'download image of experiment "%s" and channel "%s"',
            self.experiment_name, channel_name
        )
        params = {
            'plate_name': plate_name,
            'cycle_index': cycle_index,
            'well_name': well_name,
            'well_pos_x': well_pos_x,
            'well_pos_y': well_pos_y,
            'tpoint': tpoint,
            'zplane': zplane,
            'correct': correct,
            'align': align
        }
        channel_id = self._get_channel_id(channel_name)
        url = self._build_api_url(
            '/experiments/{experiment_id}/channels/{channel_id}/image-file'.format(
                experiment_id=self._experiment_id, channel_id=channel_id
            ),
            params
        )
        res = self._session.get(url)
        res.raise_for_status()
        return res

    def rename_channel(self, name, new_name):
        '''Renames a channel.

        Parameters
        ----------
        name: str
            name of the channel that should be renamed
        new_name: str
            name that should be given to the channel

        See also
        --------
        :func:`tmserver.api.channel.update_channel`
        :class:`tmlib.models.channel.Channel`
        '''
        logger.info(
            'rename channel "%s" of experiment "%s"',
            name, self.experiment_name
        )
        channel_id = self._get_channel_id(name)
        content = {'name': new_name}
        url = self._build_api_url(
            '/experiments/{experiment_id}/channels/{channel_id}'.format(
                experiment_id=self._experiment_id, channel_id=channel_id
            )
        )
        res = self._session.put(url, json=content)
        res.raise_for_status()

    def get_cycles(self):
        '''Gets cycles.

        Returns
        -------
        List[Dict[str, str]]
            information about each cycle

        See also
        --------
        :func:`tmserver.api.cycle.get_cycles`
        :class:`tmlib.models.cycles.Cycle`
        '''
        logger.info('get cycles of experiment "%s"', self.experiment_name)
        url = self._build_api_url(
            '/experiments/{experiment_id}/cycles'.format(
                experiment_id=self._experiment_id
            )
        )
        res = self._session.get(url)
        res.raise_for_status()
        return res.json()['data']

    def get_channels(self):
        '''Gets channels.

        Returns
        -------
        List[Dict[str, str]]
            information about each channel

        See also
        --------
        :func:`tmserver.api.channel.get_channels`
        :class:`tmlib.models.channel.Channel`
        '''
        logger.info('get channels of experiment "%s"', self.experiment_name)
        url = self._build_api_url(
            '/experiments/{experiment_id}/channels'.format(
                experiment_id=self._experiment_id
            )
        )
        res = self._session.get(url)
        res.raise_for_status()
        return res.json()['data']

    def _list_channels(self):
        channels = self.get_channels()
        t = PrettyTable(['ID', 'Name'])
        t.align['Name'] = 'l'
        t.padding_width = 1
        for c in channels:
            t.add_row([c['id'], c['name']])
        print(t)

    def download_channel_image(self, channel_name, plate_name,
            well_name, well_pos_y, well_pos_x,
            cycle_index=0, tpoint=0, zplane=0, correct=True, align =False):
        '''Downloads a channel image.

        Parameters
        ----------
        channel_name: str
            name of the channel
        plate_name: str
            name of the plate
        well_name: str
            name of the well
        well_pos_x: int
            zero-based x cooridinate of the acquisition site within the well
        well_pos_y: int
            zero-based y cooridinate of the acquisition site within the well
        cycle_index: str, optional
            zero-based cycle index (default: ``0``)
        tpoint: int, optional
            zero-based time point index (default: ``0``)
        zplane: int, optional
            zero-based z-plane index (default: ``0``)
        correct: bool, optional
            whether image should be corrected for illumination artifacts
            (default: ``True``)

        Note
        ----
        Image gets automatically aligned between cycles.

        Returns
        -------
        numpy.ndarray[numpy.uint16 or numpy.uint8]
            pixel/voxel array and filename

        See also
        --------
        :func:`tmserver.api.file.get_channel_image_file`
        :class:`tmlib.models.file.ChannelImageFile`
        '''
        response = self._download_channel_image(
            channel_name, plate_name, well_name, well_pos_y, well_pos_x,
            cycle_index=cycle_index, tpoint=tpoint, zplane=zplane,
            correct=correct, align = align
        )
        data = np.frombuffer(response.content, np.uint8)
        return cv2.imdecode(data, cv2.IMREAD_UNCHANGED)

    def download_channel_image_file(self, channel_name, plate_name,
            well_name, well_pos_y, well_pos_x, cycle_index,
            tpoint, zplane, correct, align, directory):
        '''Downloads a channel image and writes it to a `PNG` file on disk.

        Parameters
        ----------
        channel_name: str
            name of the channel
        plate_name: str
            name of the plate
        well_name: str
            name of the well
        well_pos_x: int
            zero-based x cooridinate of the acquisition site within the well
        well_pos_y: int
            zero-based y cooridinate of the acquisition site within the well
        cycle_index: str
            zero-based cycle index
        tpoint: int
            zero-based time point index
        zplane: int
            zero-based z-plane index
        correct: bool
            whether image should be corrected for illumination artifacts
        align: bool
            whether image should be aligned to the other cycles
        directory: str
            absolute path to the directory on disk where the file should be saved

        Note
        ----
        Image gets automatically aligned between cycles.

        See also
        --------
        :meth:`tmclient.api.TmClient.download_channel_image`
        '''
        response = self._download_channel_image(
            channel_name, plate_name, well_name, well_pos_y, well_pos_x,
            cycle_index=cycle_index, tpoint=tpoint, zplane=zplane,
            correct=correct, align = align
        )
        data = response.content
        filename = self._extract_filename_from_headers(response.headers)
        self._write_file(directory, os.path.basename(filename), data)

    def _download_segmentation_image(self, mapobject_type_name, plate_name,
            well_name, well_pos_y, well_pos_x, tpoint, zplane, align):
        logger.info(
            'download segmentation image for experiment "%s", objects "%s" at '
            'plate "%s", well "%s", y %d, x %d, tpoint %d, zplane %d, align %r',
            self.experiment_name, mapobject_type_name, plate_name, well_name,
            well_pos_y, well_pos_x, tpoint, zplane, align
        )
        params = {
            'plate_name': plate_name,
            'well_name': well_name,
            'well_pos_x': well_pos_x,
            'well_pos_y': well_pos_y,
            'tpoint': tpoint,
            'zplane': zplane,
            'align': align
        }
        mapobject_type_id = self._get_mapobject_type_id(mapobject_type_name)
        url = self._build_api_url(
            '/experiments/{experiment_id}/mapobject_types/{mapobject_type_id}/segmentations'.format(
                experiment_id=self._experiment_id,
                mapobject_type_id=mapobject_type_id
            ),
            params
        )
        res = self._session.get(url)
        res.raise_for_status()
        return res.json()['data']

    def download_segmentation_image(self, mapobject_type_name,
            plate_name, well_name, well_pos_y, well_pos_x, tpoint=0, zplane=0, align = False):
        '''Downloads a segmentation image.

        Parameters
        ----------
        plate_id: int
            ID of the parent experiment
        mapobject_type_name: str
            name of the segmented objects
        plate_name: str
            name of the plate
        well_name: str
            name of the well in which the image is located
        well_pos_y: int
            y-position of the site relative to the well grid
        well_pos_x: int
            x-position of the site relative to the well grid
        tpoint: int, optional
            zero-based time point index (default: ``0``)
        zplane: int, optional
            zero-based z-plane index (default: ``0``)
        align: bool, optional
            option to apply alignment to download

        Returns
        -------
        numpy.ndarray[numpy.int32]
            labeled image where each label encodes a segmented object

        See also
        --------
        :func:`tmserver.api.mapobject.download_segmentations`
        :class:`tmlib.models.mapobject.MapobjectSegmentation`
        '''
        response = self._download_segmentation_image(
            mapobject_type_name, plate_name, well_name, well_pos_y, well_pos_x,
            tpoint, zplane, align
        )
        return np.array(response, dtype=np.int32)

    def download_segmentation_image_file(self, mapobject_type_name,
            plate_name, well_name, well_pos_y, well_pos_x, tpoint, zplane, align,
            directory):
        '''Downloads a segmentation image and writes it to a *PNG* file on disk.

        Parameters
        ----------
        mapobject_type_name: str
            name of the segmented objects
        plate_name: str
            name of the plate
        well_name: str
            name of the well in which the image is located
        well_pos_y: int
            y-position of the site relative to the well grid
        well_pos_x: int
            x-position of the site relative to the well grid
        tpoint: int
            zero-based time point index
        zplane: int
            zero-based z-plane index
        align: bool
            option to apply alignment to download
        directory: str
            absolute path to the directory on disk where the file should be saved

        Warning
        -------
        Due to the *PNG* file format the approach is limited to images which
        contain less than 65536 objects.

        See also
        --------
        :meth:`tmclient.api.TmClient.download_segmentation_image`
        '''
        response = self._download_segmentation_image(
            mapobject_type_name, plate_name, well_name, well_pos_y, well_pos_x,
            tpoint, zplane, align
        )
        image = np.array(response, np.int32)
        if np.max(image) >= 2**16:
            raise ValueError(
                'Cannot store segmentation image as PNG file because it '
                'contains more than 65536 objects.'
            )
        filename = '{0}_{1}_{2}_y{3:03d}_x{4:03d}_z{5:03d}_t{6:03d}_{7}.png'.format(
            self.experiment_name, plate_name, well_name, well_pos_y,
            well_pos_x, zplane, tpoint, mapobject_type_name
        )
        data = cv2.imencode(filename, image.astype(np.uint16))[1]
        self._write_file(directory, filename, data)

    def _upload_segmentation_image(self, mapobject_type_name,
            plate_name, well_name, well_pos_y, well_pos_x, tpoint, zplane,
            image):
        logger.info(
            'upload segmentation image for experiment "%s", objects "%s" at '
            'plate "%s", well "%s", y %d, x %d, tpoint %d, zplane %d',
            self.experiment_name, mapobject_type_name, plate_name, well_name,
            well_pos_y, well_pos_x, tpoint, zplane
        )
        npz_file = BytesIO()
        np.savez_compressed(npz_file, segmentation=image)
        npz_file_str = base64.b64encode(npz_file.getvalue())
        # FIXME: upload npz_file directly as stream
        # REF: https://github.com/TissueMAPS/TmClient/pull/25#issuecomment-372714157
        if not isinstance(npz_file_str, str):
            # turn npz_file_str into a `str` object on Python 3.x,
            # otherwise JSON encoding below fails
            npz_file_str = npz_file_str.decode('utf-8')
        content = {
            'plate_name': plate_name,
            'well_name': well_name,
            'well_pos_x': well_pos_x,
            'well_pos_y': well_pos_y,
            'tpoint': tpoint,
            'zplane': zplane,
            'npz_file': npz_file_str
        }
        mapobject_type_id = self._get_mapobject_type_id(mapobject_type_name)
        url = self._build_api_url(
            '/experiments/{experiment_id}/mapobject_types/{mapobject_type_id}/segmentations'.format(
                experiment_id=self._experiment_id,
                mapobject_type_id=mapobject_type_id
            )
        )
        response = self._session.post(url, json=content)
        response.raise_for_status()

    def upload_segmentation_image(self, mapobject_type_name,
            plate_name, well_name, well_pos_y, well_pos_x, tpoint, zplane,
            image):
        '''Uploads a segmentation image.

        Parameters
        ----------
        mapobject_type_name: str
            name of the segmented objects
        plate_name: str
            name of the plate
        well_name: str
            name of the well in which the image is located
        well_pos_y: int
            y-position of the site relative to the well grid
        well_pos_x: int
            x-position of the site relative to the well grid
        tpoint: int, optional
            zero-based time point index (default: ``0``)
        zplane: int, optional
            zero-based z-plane index (default: ``0``)
        image: numpy.ndarray[numpy.int32]
            labeled array

        Raises
        ------
        TypeError
            when `image` is not provided in form of a `numpy` array
        ValueError
            when `image` doesn't have 32-bit unsigned integer data type

        See also
        --------
        :func:`tmserver.api.mapobject.add_segmentations`
        :class:`tmlib.models.mapobject.MapobjectSegmentation`
        '''
        if not isinstance(image, np.ndarray):
            raise TypeError('Image must be provided in form of a numpy array.')
        if image.dtype != np.int32:
            raise ValueError('Image must have 32-bit integer data type.')
        self._upload_segmentation_image(mapobject_type_name,
            plate_name, well_name, well_pos_y, well_pos_x, tpoint, zplane,
            image
        )

    def upload_segmentation_image_file(self, mapobject_type_name,
            plate_name, well_name, well_pos_y, well_pos_x, tpoint, zplane,
            filename):
        '''Uploads segmentations from a *PNG* image file.

        Parameters
        ----------
        mapobject_type_name: str
            name of the segmented objects
        plate_name: str
            name of the plate
        well_name: str
            name of the well in which the image is located
        well_pos_y: int
            y-position of the site relative to the well grid
        well_pos_x: int
            x-position of the site relative to the well grid
        tpoint: int, optional
            zero-based time point index (default: ``0``)
        zplane: int, optional
            zero-based z-plane index (default: ``0``)
        filename: str
            path to the file on disk

        Warning
        -------
        This approach will only works for images with less than 65536 objects,
        since the *PNG* format is limited to 16-bit grayscale images.

        See also
        --------
        :meth:`tmclient.api.TmClient.upload_segmentation_image`
        '''
        logger.info('upload segmentation image file "%s"', filename)
        if not filename.lower().endswith('png'):
            raise IOError('Filename must have "png" extension.')
        filename = os.path.expanduser(os.path.expandvars(filename))
        image = cv2.imread(filename, cv2.IMREAD_UNCHANGED | cv2.IMREAD_ANYDEPTH)
        self._upload_segmentation_image(
            mapobject_type_name, plate_name, well_name, well_pos_y, well_pos_x,
            tpoint, zplane, image.astype(np.int32)
        )

    def rename_feature(self, mapobject_type_name, name, new_name):
        '''Renames a feature.

        Parameters
        ----------
        mapobject_type_name: str
            name of the segmented objects type
        name: str
            name of the feature that should be renamed
        new_name: str
            name that should be given to the feature

        See also
        --------
        :func:`tmserver.api.feature.update_feature`
        :class:`tmlib.models.feature.Feature`
        '''
        logger.info(
            'rename feature "%s" of experiment "%s", mapobject type "%s"',
            name, self.experiment_name, mapobject_type_name
        )
        content = {
            'name': new_name,
        }
        feature_id = self._get_feature_id(mapobject_type_name, name)
        url = self._build_api_url(
            '/experiments/{experiment_id}/features/{feature_id}'.format(
                experiment_id=self._experiment_id, feature_id=feature_id
            )
        )
        res = self._session.put(url, json=content)
        res.raise_for_status()

    def delete_feature(self, mapobject_type_name, name):
        '''Deletes a feature.

        Parameters
        ----------
        mapobject_type_name: str
            name of the segmented objects type
        name: str
            name of the feature that should be renamed

        See also
        --------
        :func:`tmserver.api.feature.delete_feature`
        :class:`tmlib.models.feature.Feature`
        '''
        logger.info(
            'delete feature "%s" of experiment "%s", mapobject type "%s"',
            name, self.experiment_name, mapobject_type_name
        )
        feature_id = self._get_feature_id(mapobject_type_name, name)
        url = self._build_api_url(
            '/experiments/{experiment_id}/features/{feature_id}'.format(
                experiment_id=self._experiment_id, feature_id=feature_id
            )
        )
        res = self._session.delete(url)
        res.raise_for_status()

    def create_mapobject_type(self, name):
        '''Creates a mapobject type.

        Parameters
        ----------
        name: str
            name that should be given to the mapobject type

        See also
        --------
        :func:`tmserver.api.mapobject.create_mapobject_type`
        :class:`tmlib.models.mapobject.MapobjectType`
        '''
        logger.info(
            'create object type "%s" for experiment "%s"', name,
            self.experiment_name
        )
        url = self._build_api_url(
            '/experiments/{experiment_id}/mapobject_types'.format(
                experiment_id=self._experiment_id
            )
        )
        content = {'name': name}
        res = self._session.post(url, json=content)
        res.raise_for_status()
        return res.json()['data']

    def rename_mapobject_type(self, name, new_name):
        '''Renames a mapobject type.

        Parameters
        ----------
        name: str
            name of the mapobject type that should be renamed
        new_name: str
            name that should be given to the mapobject type

        See also
        --------
        :func:`tmserver.api.mapobject.update_mapobject_type`
        :class:`tmlib.models.mapobject.MapobjectType`
        '''
        logger.info(
            'rename mapobject type "%s" of experiment "%s"',
            name, self.experiment_name
        )
        content = {'name': new_name}
        mapobject_type_id = self._get_mapobject_type_id(name)
        url = self._build_api_url(
            '/experiments/{experiment_id}/mapobject_types/{mapobject_type_id}'.format(
                experiment_id=self._experiment_id,
                mapobject_type_id=mapobject_type_id
            )
        )
        res = self._session.put(url, json=content)
        res.raise_for_status()

    def delete_mapobject_type(self, name):
        '''Deletes a mapobject type.

        Parameters
        ----------
        name: str
            name of the mapobject type that should be renamed

        See also
        --------
        :func:`tmserver.api.mapobject.delete_mapobject_type`
        :class:`tmlib.models.mapobject.MapobjectType`
        '''
        logger.info(
            'delete mapobject type "%s" of experiment "%s"',
            name, self.experiment_name
        )
        mapobject_type_id = self._get_mapobject_type_id(name)
        url = self._build_api_url(
            '/experiments/{experiment_id}/mapobject_types/{mapobject_type_id}'.format(
                experiment_id=self._experiment_id,
                mapobject_type_id=mapobject_type_id
            )
        )
        res = self._session.delete(url)
        res.raise_for_status()

    def get_mapobject_types(self):
        '''Gets object types.

        Returns
        -------
        List[Dict[str, str]]
            inforamation about each mapobject type

        See also
        --------
        :func:`tmserver.api.mapobject.get_mapobject_types`
        :class:`tmlib.models.mapobject.MapobjectType`
        '''
        logger.info('get object types of experiment "%s"', self.experiment_name)
        url = self._build_api_url(
            '/experiments/{experiment_id}/mapobject_types'.format(
                experiment_id=self._experiment_id
            )
        )
        res = self._session.get(url)
        res.raise_for_status()
        return res.json()['data']

    def _list_mapobject_types(self):
        object_types = self.get_mapobject_types()
        t = PrettyTable(['ID', 'Name'])
        t.align['Name'] = 'l'
        t.padding_width = 1
        for o in object_types:
            t.add_row([o['id'], o['name']])
        print(t)

    def _info_mapobjects(self, mapobject_ids):
        t = PrettyTable([
            'ID',
            'Plate Name',
            'Well Name',
            'Site X-pos',
            'Site Y-pos',
            'Time point',
            'Z plane',
            'Label',
        ])
        t.align['Plate Name'] = 'l'
        t.align['Well Name'] = 'l'
        t.padding_width = 1
        for mapobject_id in mapobject_ids:
            try:
                data = self.get_mapobject(mapobject_id)
            except Exception as err:  # pylint: disable=broad-exception
                logger.error(
                    "Could not download location info for mapobject %s: %s",
                    mapobject_id, err)
                continue  # to next `mapobject_id`
            t.add_row([
                mapobject_id,
                data['plate_name'],
                data['well_name'],
                data['well_pos_x'],
                data['well_pos_y'],
                data['tpoint'],
                data['zplane'],
                data['label'],
            ])
        print(t)

    def get_mapobject(self, mapobject_id):
        """
        Return information about a MapObject (specified by ID).
        """
        logger.info(
            'Getting location info for mapobject %s of experiment "%s" ...',
            mapobject_id, self.experiment_name
        )
        url = self._build_api_url(
            '/experiments/{experiment_id}/mapobjects/{mapobject_id}/info'.format(
                experiment_id=self._experiment_id,
                mapobject_id=mapobject_id
            )
        )
        res = self._session.get(url)
        res.raise_for_status()
        return res.json()['data']

    def exhibit_mapobject(self, mapobject_id, ooi, channel_names,
                       extra_margin=0, palette_name="colorblind"):
        """
        Generate images of the neighborhood of a given MapObject.

        One image per channel (as given in *channel_names*) is
        generated and returned; the image contains the specified
        channel data, overlaid with segmentation contour lines for the
        MapObject types given in *ooi*.

        Idea and nitial implementation provided by Micha Mueller,
        Feb. 2019

        Parameters
        ----------
        mapobject_id: int
            Database ID of the MapObject of interest
        ooi: List[str]
            Objects of interest: show segmentation for these objects.
            (List of "mapobject type" names.)
            **Note:** The *ooi* list cannot be empty!
        channel_names: List[str]
            Channels of interest: show these channels only.
            **Note:** The *channel_names* list cannot be empty!
        extra_margin: int
            Ensure there is a margin this number of pixels wide
            around the "region of interest" which contains the
            given MapObject
        palette_name: str
            A Seaborn palette to choose colors from.
            See :func:`seaborn.color_palette` for details.

        Returns
        -------
        List[np.array]
            Channel images overlaid with segmentation contours.
        """
        # these imports are only used in this function, so it makes
        # more sense to gather them all here instead of at top-level,
        # where they would just slow-down every invocation of the module
        from seaborn import color_palette
        from skimage import img_as_ubyte
        from skimage.exposure import rescale_intensity

        metadata = self.get_mapobject(mapobject_id)
        # unpack metadata for (minimal) added efficiency
        plate_name = metadata['plate_name']
        well_name = metadata['well_name']
        well_pos_x = int(metadata['well_pos_x'])
        well_pos_y = int(metadata['well_pos_y'])
        tpoint = metadata['tpoint'] or 0
        zplane = metadata['zplane'] or 0
        try:
            label_id = int(metadata['label'])
        except (ValueError, TypeError):
            raise RuntimeError("MapObject %s has no label!" % mapobject_id)

        # determine height and width of a site containing the mapobject
        for site in self.get_sites(plate_name, well_name):
            if (well_pos_x == site['x'] and well_pos_y == site['y']):
                height = int(site['height'])
                width = int(site['width'])
                break
        else:
            raise RuntimeError(
                "No site in experiment `%s`, plate %s, well %s"
                " has the given in-well coordinates x=%d, y=%d"
                % (self.experiment, plate_name, well_name,
                   well_pos_x, well_pos_y))

        # download all channel-images and then all segmentation-images
        # for the required site into a numpy array
        # (x,y,numberofchannels)
        layers = np.zeros(
            (height, width, len(channel_names)+len(ooi)),
            dtype=np.uint16)

        for i, v in enumerate(channel_names):
            layers[:, :, i] = self.download_channel_image(
                channel_name=v,
                correct=True,
                cycle_index=0,
                # this is all extracted from metadata
                plate_name=plate_name,
                well_name=well_name,
                well_pos_x=well_pos_x,
                well_pos_y=well_pos_y,
                tpoint=tpoint,
                zplane=zplane,
            )

        # download all segmentation images for objects of interest
        for i, v in enumerate(ooi):
            layers[:, :, i+len(channel_names)] = self.download_segmentation_image(
                mapobject_type_name=v,
                align=False,
                # this is all extracted from metadata
                plate_name=plate_name,
                well_name=well_name,
                well_pos_x=well_pos_x,
                well_pos_y=well_pos_y,
                tpoint=tpoint,
                zplane=zplane,
            )

        # find the objects of interest based on the site-specific
        # label id (label_id is equal to the grayscale value of the
        # object in the downloaded segmentation image)
        def find_objects_mask(obj_type_name):
            idx = ooi.index(obj_type_name) + len(channel_names)
            return (label_id == layers[:, :, idx])
        obj_masks = map(find_objects_mask, ooi)

        # choose a ROI by discarding rows and columns that are
        # identically zero close to the border; ensure that a
        # user-specified margin is anyway kept
        def find_bounding_box(mask, margin):
            """
            Return X- and Y-coordinate ranges that enclose all nonzero points
            in 2D array `mask`.
            """
            x_range, y_range = np.where(mask != 0)
            x_min= (np.amin(x_range) - margin)
            if x_min < 0:
                x_min = 0
            x_max= (np.amax(x_range) + margin)
            if x_max > mask.shape[1]:
                x_max = mask.shape[1]
            y_min= (np.amin(y_range) - margin)
            if y_min < 0:
                y_min = 0
            y_max= (np.amax(y_range) + margin)
            if y_max > mask.shape[0]:
                y_max = mask.shape[0]
            return [x_min, x_max, y_min, y_max]
        def encasing_rectangle(r1, r2):
            """
            Return X- and Y-coordinate ranges that enclose both rectangles
            *r1* and *r2*.
            """
            return [
                which(a, b)
                for (which, a, b)
                in zip((min, max, min, max), r1, r2)
            ]
        # FIXME: this breaks if `obj_masks` has length 0
        lims = reduce(encasing_rectangle,
                      map(partial(find_bounding_box, margin=extra_margin), obj_masks))

        # crop the images to the defined ROI
        def crop(images, x_min, x_max, y_min, y_max):
            def crop1(image):
                return image[x_min:x_max, y_min:y_max]
            return map(crop1, images)
        cropped_obj_masks = crop(obj_masks, *lims)

        # find edges of segmentation of whole cell to get a line of
        # the border of the segmented object
        def find_segmentation_contours(cropped_obj_masks):
            kernel = np.ones((3,3), np.uint8)
            def outline(binary_image):
                # FIXME: this can fail with `cv2.error`, e.g.::
                #
                #     Traceback (most recent call last):
                #       [...]
                #       File ".../TissueMAPS/tmclient/src/python/tmclient/api.py", line 2214, in find_segmentation_contours
                #         return map(gradient, cropped_obj_masks)
                #       File ".../TissueMAPS/tmclient/src/python/tmclient/api.py", line 2213, in gradient
                #         kernel)
                #     cv2.error: /io/opencv/modules/core/src/matrix.cpp:991: error: (-215) dims <= 2 && step[0] > 0 in function locateROI
                #
                return cv2.morphologyEx(
                    img_as_ubyte(binary_image),
                    cv2.MORPH_GRADIENT,
                    kernel)
            return map(outline, cropped_obj_masks)
        segmentation_contours = find_segmentation_contours(cropped_obj_masks)

        # function to overlay the mask and the channel-images
        def imoverlay(img, mask, color, alpha=0.6):
            if img.ndim == 2:
                img = np.stack((img, img, img), axis=2)
            img = img_as_ubyte(rescale_intensity(img))
            overlay = img.copy()
            overlay[mask] = np.array(color) * np.max([255, np.max(img)])
            return cv2.addWeighted(img, 1-alpha, overlay, alpha, 0)

        # make the overlays of the mask of all the objects passed as
        # OOIs (object of interest)
        def all_objects_overlay(segmentation_contours, channel_image):
            colors = color_palette(palette_name, len(segmentation_contours))
            def overlay_countour_with_color(img, cc):
                countour, color = cc
                return imoverlay(img, countour.astype(np.bool), color)
            return reduce(overlay_countour_with_color,
                          zip(segmentation_contours, colors),
                          # according to Python'd doc for `reduce()`,
                          # this extra argument is prepended to the
                          # list to be reduced and serves as the `x`
                          # parameter in the first calculation
                          channel_image)

        # make list of np arrays containing all channels overlayed with the mask of all OOIs
        x_min, x_max, y_min, y_max = lims
        def overlay_segmentation_contours_on_layer(layer_idx):
            return all_objects_overlay(
                segmentation_contours,
                layers[x_min:x_max, y_min:y_max, layer_idx])
        channels_with_overlaid_segmentation = map(
            overlay_segmentation_contours_on_layer, range(len(channel_names)))

        return channels_with_overlaid_segmentation

    def _exhibit_mapobjects(self, mapobject_ids, object_types, channel_names,
                        extra_margin=0, save=True, show=False,
                        file_name_format='{mapobject_id}_{channel_name}.png',
                        grid_columns=1):
        """
        Save and interactively display images
        of the neighborhood of a given MapObject.

        This method is meant to be the command-line interface for
        :func:`exhibit_mapobjects` and should likely not be used in
        Python programming.

        Parameters
        ----------
        mapobject_ids: List[str]
          List of database IDs of the MapObjects of interest
        object_types: str
          Comma-separated list of MapObject types whose segmentation
          should be shown on the images.  Cannot be empty.
        channel_names: str
          Comma-separated list of channels names to save and/or show.
          If empty (or any other ``False`` value), use all channels.
        extra_margin: int
          Select displayed region by allowing this number of pixels
          around all objects of interest.
        save: bool
          Whether images should be saved to file(s).
          At least one among this and *show* should be true.
          Use *file_name_format* to specify the output file names.
        show: bool
          Whether to interactively show images.
          At least one among this and *save* should be true.
        file_name_format: str
          Format string for specifying output file names.
          The following substrings will be substituted with
          actual values in the format string:
          - ``{mapobject_id}``: Database ID of the MapObject,
            as given by the *mapobject_id* argument
          - ``{channel_name}``: Name of the channel on which
            segmentation contours are overlaid.
          - ``{index}``: Index (0-based) of images being saved.
          - ``{total}``: Total number of images to save.
        grid_columns: int
          If showing images, arrange them in a grid with this
          many columns. (Default 1, meaning display all images
          in a vertical strip.)
        """
        # these imports are only used in this function, so it makes
        # more sense to gather them all here instead of at top-level,
        # where they would just slow-down every invocation of the module
        import matplotlib.pyplot as plt
        from scipy.misc import imsave

        assert save or show, (
            "At least one of the two parameters"
            " `save` and `show` should be true!")

        if isinstance(object_types, basestring):
            object_types = object_types.split(',')

        if isinstance(channel_names, basestring):
            channel_names = channel_names.split(',')
        if not channel_names:
            channel_names = [
                channel_info['name']
                for channel_info in self.get_channels()
            ]

        result = []
        for mapobject_id in mapobject_ids:
            images = self.exhibit_mapobject(
                mapobject_id, object_types, channel_names, extra_margin)
            n = len(images)
            assert n == len(channel_names), (
                "BUG: More images ({}) were returned by `self.show_mapobject()`"
                " than channels were requested ({})."
                .format(n, len(channel_names))
            )

            # save the channel images and name them with the channel and the mapobject_id
            if save:
                logger.debug("Saving images ...")
                for i in range(n):
                    img_file_name = file_name_format.format(
                        # make parameter names available in fmt string
                        mapobject_id=mapobject_id,
                        channel_name=channel_names[i],
                        index=i,
                        total=n,
                        # shortcut aliases
                        mapobject=mapobject_id,
                        channel=channel_names[i],
                        i=i,
                        tot=n,
                    )
                    logger.info("Saving channel %s into file `%s` ...",
                                channel_names[i], img_file_name)
                    imsave(img_file_name, images[i])

            # show all the channel images
            if show:
                ncols = grid_columns
                nrows = int(n / ncols)
                logger.info("Showing %d images on a %dx%d grid...", n, nrows, ncols)
                fig, axes = plt.subplots(
                    nrows, ncols, sharex=True, sharey=True,
                    squeeze=False, figsize=[4*ncols, 3*nrows])
                for row in range(nrows):
                    for col in range(ncols):
                        idx = row*ncols + col
                        if idx >= n:
                            break
                        ax = axes[row][col]
                        image = images[idx]
                        if image.ndim == 2:
                            plt.gray()
                        ax.imshow(image)
                        ax.set_title(channel_names[idx])
                result.append(plt.show())

        return result

    def get_features(self, mapobject_type_name):
        '''Gets features for a given object type.

        Parameters
        ----------
        mapobject_type_name: str
            type of the segmented objects

        Returns
        -------
        List[Dict[str, str]]
            information about each feature

        See also
        --------
        :func:`tmserver.api.feature.get_features`
        :class:`tmlib.models.feature.Feature`
        '''
        logger.info(
            'get features of experiment "%s", object type "%s"',
            self.experiment_name, mapobject_type_name
        )
        mapobject_type_id = self._get_mapobject_type_id(mapobject_type_name)
        url = self._build_api_url(
            '/experiments/{experiment_id}/mapobject_types/{mapobject_type_id}/features'.format(
                experiment_id=self._experiment_id,
                mapobject_type_id=mapobject_type_id
            )
        )
        res = self._session.get(url)
        res.raise_for_status()
        return res.json()['data']

    def _list_features(self, mapobject_type_name):
        features = self.get_features(mapobject_type_name)
        t = PrettyTable(['ID', 'Name'])
        t.align['Name'] = 'l'
        t.padding_width = 1
        for f in features:
            t.add_row([f['id'], f['name']])
        print(t)

    def _download_feature_values(self, mapobject_type_name,
            plate_name=None, well_name=None, well_pos_y=None, well_pos_x=None,
            tpoint=None):
        logger.info(
            'download features values for experiment "%s" and object type "%s"',
            self.experiment_name, mapobject_type_name
        )
        params = dict()
        if plate_name is not None:
            params['plate_name'] = plate_name
        if well_name is not None:
            params['well_name'] = well_name
        if well_pos_y is not None:
            params['well_pos_y'] = well_pos_y
        if well_pos_x is not None:
            params['well_pos_x'] = well_pos_x
        if tpoint is not None:
            params['tpoint'] = tpoint
        mapobject_type_id = self._get_mapobject_type_id(mapobject_type_name)
        url = self._build_api_url(
            '/experiments/{experiment_id}/mapobject_types/{mapobject_type_id}/feature-values'.format(
                experiment_id=self._experiment_id,
                mapobject_type_id=mapobject_type_id
            ),
            params
        )
        res = self._session.get(url, stream=True)
        res.raise_for_status()
        return res

    def _upload_feature_values(self, mapobject_type_name, plate_name,
            well_name, well_pos_y, well_pos_x, tpoint, data):
        logger.info(
            'upload feature values for experiment "%s", object type "%s" at '
            'plate "%s", well "%s", y %d, x %d, tpoint %d',
            self.experiment_name, mapobject_type_name, plate_name, well_name,
            well_pos_y, well_pos_x, tpoint
        )
        content = {
            'plate_name': plate_name, 'well_name': well_name,
            'well_pos_y': well_pos_y, 'well_pos_x': well_pos_x,
            'tpoint': tpoint,
            'names': data.columns.tolist(),
            'labels': data.index.tolist(),
            'values': data.values.tolist()
        }
        mapobject_type_id = self._get_mapobject_type_id(mapobject_type_name)
        url = self._build_api_url(
            '/experiments/{experiment_id}/mapobject_types/{mapobject_type_id}/feature-values'.format(
                experiment_id=self._experiment_id,
                mapobject_type_id=mapobject_type_id
            )
        )
        res = self._session.post(url, json=content)
        res.raise_for_status()

    def upload_feature_value_file(self, mapobject_type_name, plate_name,
            well_name, well_pos_y, well_pos_x, tpoint, filename, index_col):
        '''Uploads feature values for the given
        :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>` at the
        specified :class:`Site <tmlib.models.site.Site>`.

        Parameters
        ----------
        mapobject_type_name: str
            type of the segmented objects
        plate_name: str
            name of the plate
        well_name: str
            name of the well
        well_pos_y: int
            y-position of the site relative to the well grid
        well_pos_x: int
            x-position of the site relative to the well grid
        tpoint: int
            zero-based time point index
        filename: str
            path to the file on disk
        index_col: str
            column name containing the object labels

        See also
        --------
        :func:`tmserver.api.feature.add_feature_values`
        :class:`tmlib.models.feature.FeatureValues`
        '''
        logger.info('upload feature value file "%s"', filename)
        if not filename.lower().endswith('csv'):
            raise IOError('Filename must have "csv" extension.')
        filename = os.path.expanduser(os.path.expandvars(filename))
        data = pd.read_csv(filename, index_col=index_col)
        self._upload_feature_values(
            mapobject_type_name, plate_name, well_name, well_pos_y, well_pos_x,
            tpoint, data
        )


    def download_feature_values(self, mapobject_type_name,
            plate_name=None, well_name=None, well_pos_y=None, well_pos_x=None,
            tpoint=None):
        '''Downloads feature values for the given
        :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`.

        Parameters
        ----------
        mapobject_type_name: str
            type of the segmented objects
        plate_name: str, optional
            name of the plate
        well_name: str, optional
            name of the well
        well_pos_y: int, optional
            y-position of the site relative to the well grid
        well_pos_x: int, optional
            x-position of the site relative to the well grid
        tpoint: int, optional
            zero-based time point index

        Returns
        -------
        pandas.DataFrame
            *n*x*p* dataframe, where *n* are number of objects and *p* number
            of features

        See also
        --------
        :func:`tmserver.api.feature.get_feature_values`
        :class:`tmlib.models.feature.FeatureValues`

        Warning
        -------
        This will try to load all data into memory, which may be problematic
        for large datasets.
        '''
        res = self._download_feature_values(
            mapobject_type_name, plate_name, well_name, well_pos_y, well_pos_x,
            tpoint
        )
        logger.debug('decode CSV data')
        file_obj = StringIO(res.content.decode('utf-8'))
        try:
            return pd.read_csv(file_obj)
        except EmptyDataError:
            return pd.DataFrame()

    def download_feature_values_and_metadata_files(self, mapobject_type_name,
                                                   directory, parallel=1):
        '''Downloads all feature values for the given object type and stores the
        data as *CSV* files on disk.

        Parameters
        ----------
        mapobject_type_name: str
            type of the segmented objects
        directory: str
            absolute path to the directory on disk where the file should be
        parallel: int
            number of parallel processes to use for upload

        See also
        --------
        :meth:`tmclient.api.TmClient.download_feature_values`
        :meth:`tmclient.api.TmClient.download_object_metadata`
        '''

        def download_per_well(well):
            logger.info(
                'download feature data at well: plate=%s, well=%s',
                well['plate_name'], well['name']
            )
            res = self._download_feature_values(
                mapobject_type_name, well['plate_name'], well['name']
            )
            filename = self._extract_filename_from_headers(res.headers)
            filepath = os.path.join(directory, os.path.basename(filename))
            logger.info('write feature values to file: %s', filepath)
            with open(filepath, 'wb') as f:
                for c in res.iter_content(chunk_size=1000):
                    f.write(c)

            logger.info(
                'download feature metadata at well: plate=%s, well=%s',
                well['plate_name'], well['name']
            )
            res = self._download_object_metadata(
                mapobject_type_name, well['plate_name'], well['name']
            )
            filename = self._extract_filename_from_headers(res.headers)
            filepath = os.path.join(directory, os.path.basename(filename))
            logger.info('write metadata to file: %s', filepath)
            with open(filepath, 'wb') as f:
                for c in res.iter_content(chunk_size=1000):
                    f.write(c)

        work = [(download_per_well, well) for well in self.get_wells()]
        self._parallelize(work, parallel)
        # TODO: Store site-specific files in temporary directory and afterwards
        # merge them into a single file in the directory sprecified by the user.

    def _download_object_metadata(self, mapobject_type_name, plate_name=None,
            well_name=None, well_pos_y=None, well_pos_x=None, tpoint=None):
        logger.info(
            'download metadata for experiment "%s" and object type "%s"',
            self.experiment_name, mapobject_type_name
        )
        params = dict()
        if plate_name is not None:
            params['plate_name'] = plate_name
        if well_name is not None:
            params['well_name'] = well_name
        if well_pos_y is not None:
            params['well_pos_y'] = well_pos_y
        if well_pos_x is not None:
            params['well_pos_x'] = well_pos_x
        if tpoint is not None:
            params['tpoint'] = tpoint
        mapobject_type_id = self._get_mapobject_type_id(mapobject_type_name)
        url = self._build_api_url(
            '/experiments/{experiment_id}/mapobject_types/{mapobject_type_id}/metadata'.format(
                experiment_id=self._experiment_id,
                mapobject_type_id=mapobject_type_id
            ),
            params
        )
        res = self._session.get(url, stream=True)
        res.raise_for_status()
        return res

    def download_object_metadata(self, mapobject_type_name, plate_name=None,
            well_name=None, well_pos_y=None, well_pos_x=None, tpoint=None):
        '''Downloads metadata for the given object type, which describes the
        position of each segmented object on the map.

        Parameters
        ----------
        mapobject_type_name: str
            type of the segmented objects
        plate_name: str, optional
            name of the plate
        well_name: str, optional
            name of the well
        well_pos_y: int, optional
            y-position of the site relative to the well grid
        well_pos_x: int, optional
            x-position of the site relative to the well grid
        tpoint: int, optional
            zero-based time point index

        Returns
        -------
        pandas.DataFrame
            *n*x*p* dataframe, where *n* are number of objects and *p* number
            of metadata attributes

        See also
        --------
        :func:`tmserver.api.feature.get_metadata`
        '''
        res = self._download_object_metadata(
            mapobject_type_name, plate_name, well_name, well_pos_y, well_pos_x,
            tpoint
        )
        file_obj = StringIO(res.content.decode('utf-8'))
        try:
            return pd.read_csv(file_obj)
        except EmptyDataError:
            return pd.DataFrame()

    def download_workflow_description(self):
        '''Downloads the workflow description. In case no description has been
        uploaded so far, the server sends a default template.

        Returns
        -------
        dict
            workflow description

        See also
        --------
        :func:`tmserver.api.workflow.get_workflow_description`
        :class:`tmlib.workflow.description.WorkflowDescription`
        '''
        logger.info(
            'download description for workflow of experiment "%s"',
            self.experiment_name
        )
        url = self._build_api_url(
            '/experiments/{experiment_id}/workflow/description'.format(
                experiment_id=self._experiment_id
            )
        )
        res = self._session.get(url)
        res.raise_for_status()
        return res.json()['data']

    def download_workflow_description_file(self, filename):
        '''Downloads the workflow description and writes it to a *YAML* file.

        Parameters
        ----------
        filename: str
            path to the file to which description should be written

        See also
        --------
        :meth:`tmclient.api.TmClient.download_workflow_description`
        '''
        description = self.download_workflow_description()
        logger.info('write workflow description to file: %s', filename)
        with open(filename, 'w') as f:
            content = yaml.safe_dump(
                description, default_flow_style=False, explicit_start=True
            )
            f.write(content)

    def upload_workflow_description(self, description):
        '''Uploads a workflow description.

        Parameters
        ----------
        dict
            workflow description

        See also
        --------
        :func:`tmserver.api.workflow.update_workflow_description`
        :class:`tmlib.workflow.description.WorkflowDescription`
        '''
        logger.info(
            'upload descpription for workflow of experiment "%s"',
            self.experiment_name
        )
        content = {'description': description}
        url = self._build_api_url(
            '/experiments/{experiment_id}/workflow/description'.format(
                experiment_id=self._experiment_id
            )
        )
        res = self._session.post(url, json=content)
        res.raise_for_status()

    def upload_workflow_description_file(self, filename):
        '''Uploads workflow description from a *YAML* file.

        Parameters
        ----------
        filename: str
            path to the file from which description should be read

        See also
        --------
        :meth:`tmclient.api.TmClient.upload_workflow_description`
        '''
        if (
            not filename.lower().endswith('yml') and
            not filename.lower().endswith('yaml')
        ):
            raise ResourceError('filename must have "yaml" or "yml" extension')
        with open(filename) as f:
            logger.info('load workflow description from file: %s', filename)
            description = yaml.safe_load(f.read())
        self.upload_workflow_description(description)

    def submit_workflow(self, description=None):
        '''Submits the workflow.

        Parameters
        ----------
        description: dict, optional
            workflow description

        See also
        --------
        :func:`tmserver.api.workflow.submit_workflow`
        :class:`tmlib.workflow.workflow.Workflow`
        '''
        logger.info('submit workflow of experiment "%s"', self.experiment_name)
        content = dict()
        if description is not None:
            content['description'] = description
        url = self._build_api_url(
            '/experiments/{experiment_id}/workflow/submit'.format(
                experiment_id=self._experiment_id
            )
        )
        res = self._session.post(url, json=content)
        res.raise_for_status()

    def resubmit_workflow(self, stage_name=None, description=None):
        '''Resubmits the workflow.

        Parameters
        ----------
        stage_name: str, optional
            name of the stage at which workflow should be resubmitted
            (when omitted workflow will be restarted from the beginning)
        description: dict, optional
            workflow description

        See also
        --------
        :func:`tmserver.api.workflow.resubmit_workflow`
        :class:`tmlib.workflow.workflow.Workflow`
        '''
        logger.info(
            'resubmit workflow of experiment "%s"', self.experiment_name
        )
        content = dict()
        if description is not None:
            content['description'] = description
        if stage_name is not None:
            content['stage_name'] = stage_name
        url = self._build_api_url(
            '/experiments/{experiment_id}/workflow/resubmit'.format(
                experiment_id=self._experiment_id
            )
        )
        res = self._session.post(url, json=content)
        res.raise_for_status()

    def kill_workflow(self):
        '''Kills the workflow.

        See also
        --------
        :func:`tmserver.api.workflow.kill_workflow`
        :class:`tmlib.workflow.workflow.Workflow`
        '''
        logger.info('kill workflow of experiment "%s"', self.experiment_name)
        content = dict()
        url = self._build_api_url(
            '/experiments/{experiment_id}/workflow/kill'.format(
                experiment_id=self._experiment_id
            )
        )
        res = self._session.post(url)
        res.raise_for_status()

    def get_workflow_status(self, depth=2):
        '''Gets the workflow status.

        Parameters
        ----------
        depth: int, optional
            query depth - in which detail status of subtasks will be queried

        Returns
        -------
        dict
            status information about the workflow

        See also
        --------
        :func:`tmserver.api.workflow.get_workflow_status`
        :func:`tmlib.workflow.utils.get_task_status`
        :class:`tmlib.models.submission.Task`
        '''
        logger.info(
            'get status for workflow of experiment "%s"', self.experiment_name
        )
        params = {'depth': depth}
        url = self._build_api_url(
            '/experiments/{experiment_id}/workflow/status'.format(
                experiment_id=self._experiment_id
            ),
            params
        )
        res = self._session.get(url)
        res.raise_for_status()
        return res.json()['data']

    def _show_workflow_status(self, depth):
        status = self.get_workflow_status(depth)

        def add_row_recursively(data, table):
            table.add_row([
                data['id'],
                data['name'],
                data['type'],
                data['created_at'],
                data['updated_at'],
                data['state'],
                '{0:.2f}'.format(data['percent_done']),
                data['exitcode'] if data['exitcode'] is not None else '',
                data['time'] if data['time'] is not None else '',
                data['cpu_time'] if data['cpu_time'] is not None else '',
                data['memory'] if data['memory'] is not None else ''
            ])
            for subtd in data.get('subtasks', list()):
                if subtd is None:
                    continue
                add_row_recursively(subtd, table)

        t = PrettyTable([
            'ID', 'Name', 'Type', 'Created (YYYY-MM-DD HH:MM:SS)',
            'Finished (YYYY-MM-DD HH:MM:SS)', 'State', 'Done (%)',
            'Exitcode', 'Wall Time (HH:MM:SS)', 'CPU Time (HH:MM:SS)',
            'Memory (MB)'
        ])
        t.align['ID'] = 'l'
        t.align['Name'] = 'l'
        t.align['Type'] = 'l'
        t.align['State'] = 'l'
        t.align['Done (%)'] = 'r'
        t.align['Memory (MB)'] = 'r'
        t.padding_width = 1
        if status:
            add_row_recursively(status, t)
        print(t)

    def _get_workflow_job_id(self, step_name, name):
        logger.debug(
            'get job ID for experiment "%s" and job "%s"',
            self.experiment_name, name
        )
        params = {'step_name': step_name, 'name': name}
        url = self._build_api_url(
            '/experiments/{experiment_id}/workflow/jobs'.format(
                experiment_id=self._experiment_id
            ),
            params
        )
        res = self._session.get(url)
        res.raise_for_status()
        data = res.json()['data']
        if len(data) > 1:
            raise ResourceError(
                'More than one job found with name "{0}" for step "{1}"'.format(
                    name, step_name
                )
            )
        elif len(data) == 0:
            raise ResourceError(
                'No job found with name "{0}" for step "{1}"'.format(
                    name, step_name
                )
            )
        return data[0]['id']

    def _show_workflow_job_log(self, step_name, name):
        logger.info(
            'get log output for job "%s" of workflow step "%s"', name, step_name
        )
        job_id = self._get_workflow_job_id(step_name, name)
        url = self._build_api_url(
            '/experiments/{experiment_id}/workflow/jobs/{job_id}/log'.format(
                experiment_id=self._experiment_id, job_id=job_id
            )
        )
        res = self._session.get(url)
        res.raise_for_status()
        data = res.json()['data']
        print('\nSTANDARD OUTPUT\n===============')
        print(data['stdout'])
        print('\nSTANDARD ERROR\n==============')
        print(data['stderr'])

    def download_jterator_project(self):
        '''Downloads the *jterator* project.

        Returns
        -------
        dict
            "pipeline" description and a "handles" descriptions for each module
            in the pipeline

        See also
        --------
        :func:`tmserver.api.workflow.get_jterator_project`
        :class:`tmlib.workflow.jterator.description.PipelineDescription`
        :class:`tmlib.workflow.jterator.description.HandleDescriptions`
        '''
        logger.info(
            'download jterator project of experiment "%s"', self.experiment_name
        )
        url = self._build_api_url(
            '/experiments/{experiment_id}/workflow/jtproject'.format(
                experiment_id=self._experiment_id
            )
        )
        res = self._session.get(url)
        res.raise_for_status()
        return res.json()['data']

    def upload_jterator_project(self, pipeline, handles):
        '''Uploads a *jterator* project.

        Parameters
        ----------
        pipeline: dict
            description of the jterator pipeline
        handles: dict, optional
            description of each module in the jterator pipeline

        See also
        --------
        :func:`tmserver.api.workflow.update_jterator_project`
        :class:`tmlib.workflow.jterator.description.PipelineDescription`
        :class:`tmlib.workflow.jterator.description.HandleDescriptions`
        '''
        logger.info(
            'upload jterator project for experiment "%s"', self.experiment_name
        )
        content = {
            'pipeline': pipeline,
            'handles': handles
        }
        url = self._build_api_url(
            '/experiments/{experiment_id}/workflow/jtproject'.format(
                experiment_id=self._experiment_id
            )
        )
        res = self._session.put(url, json=content)
        res.raise_for_status()

    def download_jterator_project_files(self, directory):
        '''Downloads the *jterator* project and stores it
        on disk in YAML format. The pipeline description will be stored
        in a ``pipeline.yaml`` file in `directory` and each handle description
        will be stored in a ``*handles.yaml`` file and placed into a ``handles``
        subfolder of `directory`.

        Parameters
        ----------
        directory: str
            path to the root folder where files should be stored

        See also
        --------
        :meth:`tmclient.api.TmClient.download_jterator_project`
        '''
        descriptions = self.download_jterator_project()
        directory = os.path.expanduser(os.path.expandvars(directory))

        logger.info(
            'store jterator project description in directory: %s', directory
        )
        if not os.path.exists(directory):
            raise OSError('Directory does not exit: {0}'.format(directory))

        pipeline_filename = os.path.join(directory, 'pipeline.yaml')
        logger.debug('write pipeline description to file: %s', pipeline_filename)
        with open(pipeline_filename, 'w') as f:
            content = yaml.safe_dump(
                descriptions['pipeline'],
                explicit_start=True, default_flow_style=False
            )
            f.write(content)

        handles_subdirectory = os.path.join(directory, 'handles')
        if not os.path.exists(handles_subdirectory):
            logger.debug('create "handles" directory')
            os.mkdir(handles_subdirectory)
        for name, description in descriptions['handles'].items():
            handles_filename = os.path.join(
                handles_subdirectory, '{name}.handles.yaml'.format(name=name)
            )
            logger.debug(
                'write handles description to file: %s', handles_filename
            )
            with open(handles_filename, 'w') as f:
                content = yaml.safe_dump(
                    description,
                    explicit_start=True, default_flow_style=False
                )
                f.write(content)

    def upload_jterator_project_files(self, directory):
        '''Uploads the *jterator* project description from files on disk in
        YAML format. It expects a ``pipeline.yaml`` file in `directory` and
        optionally ``*handles.yaml`` files in a ``handles`` subfolder of
        `directory`.

        Parameters
        ----------
        directory: str
            path to the root folder where files are located

        See also
        --------
        :meth:`tmclient.api.TmClient.upload_jterator_project`
        '''
        logger.info(
            'load jterator project description from directory: %s', directory
        )
        if not os.path.exists(directory):
            raise OSError('Directory does not exit: {0}'.format(directory))

        pipeline_filename = os.path.join(directory, 'pipeline.yaml')
        if not os.path.exists(pipeline_filename):
            raise OSError(
                'Pipeline description file does not exist: {0}'.format(
                    pipeline_filename
                )
            )
        logger.debug('load pipeline filename: %s', pipeline_filename)
        with open(pipeline_filename) as f:
            pipeline_description = yaml.safe_load(f.read())

        handles_subdirectory = os.path.join(directory, 'handles')
        if not os.path.exists(handles_subdirectory):
            logger.warn(
                'handles subdirectory does not exist: %s', handles_subdirectory
            )
        handles_filename_pattern = os.path.join(
            handles_subdirectory, '*.handles.yaml'
        )
        handles_descriptions = dict()
        for handles_filename in glob.glob(handles_filename_pattern):
            name = os.path.splitext(os.path.splitext(
                os.path.basename(handles_filename)
            )[0])[0]
            logger.debug('load handles file: %s', handles_filename)
            with open(handles_filename) as f:
                handles_descriptions[name] = yaml.safe_load(f.read())

        self.upload_jterator_project(
            pipeline_description, handles_descriptions
        )

    def _get_tool_job_id(self, name):
        logger.debug(
            'get tool result ID for experiment "%s" and result "%s"',
            self.experiment_name, name
        )
        params = {'name': name}
        url = self._build_api_url(
            '/experiments/{experiment_id}/tools/results'.format(
                experiment_id=self._experiment_id
            ),
            params
        )
        res = self._session.get(url)
        res.raise_for_status()
        data = res.json()['data']
        if len(data) > 1:
            raise ResourceError(
                'More than one tool result found with name "{0}"'.format(name)
            )
        elif len(data) == 0:
            raise ResourceError(
                'No tool results found with name "{0}"'.format(name)
            )
        return data[0]['id']

    def get_tool_results(self):
        '''Gets tool results.

        Returns
        -------
        List[Dict[str, str]]
            information about each tool result

        See also
        --------
        :func:`tmserver.api.tools.get_tool_results`
        :class:`tmlib.models.result.ToolResult`
        '''
        logger.info('get tool results of experiment "%s"', self.experiment_name)
        url = self._build_api_url(
            '/experiments/{experiment_id}/tools/results'.format(
                experiment_id=self._experiment_id
            )
        )
        res = self._session.get(url)
        res.raise_for_status()
        return res.json()['data']

    def _list_tool_results(self):
        results = self.get_tool_results()
        t = PrettyTable(['ID', 'Name'])
        t.align['Name'] = 'l'
        t.padding_width = 1
        for r in results:
            t.add_row([r['id'], r['name']])
        print(t)

    def get_tools_status(self, tool_name=None):
        '''Gets the status of tool jobs.

        Parameters
        ----------
        tool_name: str, optional
            filter jobs by tool name

        Returns
        -------
        dict
            status information about tool jobs

        See also
        --------
        :func:`tmserver.api.tools.get_tools_status`
        :func:`tmlib.workflow.utils.get_task_status`
        :class:`tmlib.models.submission.Task`
        '''
        logger.info(
            'get status for tools of experiment "%s"', self.experiment_name
        )
        params = dict()
        if tool_name is not None:
            params['tool_name'] = tool_name
        url = self._build_api_url(
            '/experiments/{experiment_id}/tools/jobs'.format(
                experiment_id=self._experiment_id
            ),
            params
        )
        res = self._session.get(url)
        res.raise_for_status()
        return res.json()['data']

    def _get_tool_job_id(self, name, submission_id):
        logger.debug(
            'get job ID for experiment "%s", job "%s" and submission %d',
            self.experiment_name, name, submission_id
        )
        params = {'name': name, 'submission_id': submission_id}
        url = self._build_api_url(
            '/experiments/{experiment_id}/tools/jobs'.format(
                experiment_id=self._experiment_id
            ),
            params
        )
        res = self._session.get(url)
        res.raise_for_status()
        data = res.json()['data']
        if len(data) > 1:
            raise ResourceError(
                'More than one job found with name "{0}" for '
                'submission {1}'.format(name, submission_id)
            )
        elif len(data) == 0:
            raise ResourceError(
                'No job found with name "{0}" for submission {1}'.format(
                    name, submission_id
                )
            )
        return data[0]['id']

    def _show_tools_status(self, tool_name):
        status = self.get_tools_status(tool_name)

        t = PrettyTable([
            'ID', 'Name', 'Submission Number', 'Submission Date',
            'State', 'ExitCode',
            'Time (HH:MM:SS)', 'CPU Time (HH:MM:SS)', 'Memory (MB)'
        ])
        t.align['ID'] = 'l'
        t.align['Name'] = 'l'
        t.align['Submission Number'] = 'r'
        t.align['Submission Date'] = 'l'
        t.align['State'] = 'l'
        t.align['Done (%)'] = 'r'
        t.align['Memory (MB)'] = 'r'
        t.padding_width = 1
        for data in status:
            t.add_row([
                data['id'],
                data['name'],
                data['submission_id'],
                data['submitted_at'],
                data['state'],
                data['exitcode'] if data['exitcode'] is not None else '',
                data['time'] if data['time'] is not None else '',
                data['cpu_time'] if data['cpu_time'] is not None else '',
                data['memory'] if data['memory'] is not None else ''
            ])
        print(t)

    def _show_tool_job_log(self, submission_id, name):
        logger.info(
            'get log output for job "%s" of submission %d', name, submission_id
        )
        job_id = self._get_tool_job_id(name, submission_id)
        url = self._build_api_url(
            '/experiments/{experiment_id}/tools/jobs/{job_id}/log'.format(
                experiment_id=self._experiment_id, job_id=job_id
            )
        )
        res = self._session.get(url)
        res.raise_for_status()
        data = res.json()['data']
        print('\nSTANDARD OUTPUT\n===============')
        print(data['stdout'])
        print('\nSTANDARD ERROR\n==============')
        print(data['stderr'])
