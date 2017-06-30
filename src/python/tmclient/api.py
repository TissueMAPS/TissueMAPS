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
import inspect
import logging
import sys
import os
import cgi
import re
import json
import glob
try:
    # NOTE: Python3 no longer has the cStringIO module
    from cStringIO import StringIO
except ImportError:
    from io import StringIO

import requests
import yaml
import cv2
import pandas as pd
from pandas.io.common import EmptyDataError
import numpy as np
from prettytable import PrettyTable

from tmclient.base import HttpClient
from tmclient.log import configure_logging
from tmclient.log import map_logging_verbosity
from tmclient.errors import ResourceError


logger = logging.getLogger(__name__)


class TmClient(HttpClient):

    '''*TissueMAPS* RESTful API client.'''

    def __init__(self, host, port, username, password=None, experiment_name=None):
        '''
        Parameters
        ----------
        host: str
            name or IP address of the machine that hosts the *TissueMAPS* server
            (e.g. ``"localhost"`` or ``127.0.0.1``)
        port: int
            number of the port to which *TissueMAPS* server listens
            (e.g. ``8002``)
        username: str
            name of the user
        password: str
            password for the user (can also be provided via the
            *tm_pass* file)
        experiment_name: str, optional
            name of the experiment that should be accessed

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
        super(TmClient, self).__init__(host, port, username, password)
        self.experiment_name = experiment_name

    @property
    def experiment_name(self):
        '''str: name of the currently accessed experiment'''
        if self._experiment_name is None:
            logger.warn('experiment name is not set')
            raise AttributeError('Attribute experiment_name is not set.')
        return self._experiment_name

    @experiment_name.setter
    def experiment_name(self, value):
        self._experiment_name = value

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

        try:
            client = cls(
                args.host, args.port, args.username, args.password
            )
            if hasattr(args, 'experiment_name'):
                client.experiment_name = args.experiment_name
            client(args)
        except requests.exceptions.HTTPError as err:
            logger.error(str(err))
            sys.exit(1)
        except ResourceError as err:
            logger.error(str(err).lower())
            sys.exit(1)
        except Exception as err:
            logger.error(str(err).lower())
            sys.exit(1)

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

    def upload_microscope_files(self, plate_name, acquisition_name, directory):
        '''Uploads microscope files contained in `directory`.

        Parameters
        ----------
        plate_name: str
            name of the parent plate
        acquisition_name: str
            name of the parent acquisition
        directory: int
            path to a directory on disk where the files that should be uploaded
            are located

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
        # TODO: consider using os.walk() to screen subdirectories recursively
        logger.info(
            'upload microscope files for experiment "%s", plate "%s" '
            'and acquisition "%s"',
            self.experiment_name, plate_name, acquisition_name
        )
        acquisition_id = self._get_acquisition_id(plate_name, acquisition_name)

        def upload_file(filepath):
            logger.info('upload file: %s', os.path.basename(filepath))
            self._upload_file(acquisition_id, filepath)

        directory = os.path.expanduser(directory)
        directory = os.path.expandvars(directory)
        filenames = [
            f for f in os.listdir(directory)
            if not os.path.isdir(f) and not f.startswith('.')
        ]
        registered_filenames = self._register_files_for_upload(
            acquisition_id, filenames
        )
        logger.info('registered %d files', len(registered_filenames))

        args = [(os.path.join(directory, name), ) for name in filenames]
        self._parallelize(upload_file, args)

        return registered_filenames

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

    def _upload_file(self, acquisition_id, filepath):
        logger.debug('upload file: %s', filepath)
        url = self._build_api_url(
            '/experiments/{experiment_id}/acquisitions/{acquisition_id}/microscope-file'.format(
                experiment_id=self._experiment_id, acquisition_id=acquisition_id
            )
        )
        files = {'file': open(filepath, 'rb')}
        res = self._session.post(url, files=files)
        res.raise_for_status()

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
            cycle_index=0, tpoint=0, zplane=0, correct=True):
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
            'correct': correct
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
            cycle_index=0, tpoint=0, zplane=0, correct=True):
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
            correct=correct
        )
        data = np.frombuffer(response.content, np.uint8)
        return cv2.imdecode(data, cv2.IMREAD_UNCHANGED)

    def download_channel_image_file(self, channel_name, plate_name,
            well_name, well_pos_y, well_pos_x, cycle_index,
            tpoint, zplane, correct, directory):
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
            correct=correct
        )
        data = response.content
        filename = self._extract_filename_from_headers(response.headers)
        self._write_file(directory, filename, data)

    def _download_segmentation_image(self, mapobject_type_name, plate_name,
            well_name, well_pos_y, well_pos_x, tpoint, zplane):
        logger.info(
            'download segmentation image for experiment "%s", objects "%s" at '
            'plate "%s", well "%s", y %d, x %d, tpoint %d, zplane %d',
            self.experiment_name, mapobject_type_name, plate_name, well_name,
            well_pos_y, well_pos_x, tpoint, zplane
        )
        params = {
            'plate_name': plate_name,
            'well_name': well_name,
            'well_pos_x': well_pos_x,
            'well_pos_y': well_pos_y,
            'tpoint': tpoint,
            'zplane': zplane
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
            plate_name, well_name, well_pos_y, well_pos_x, tpoint=0, zplane=0):
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
            tpoint, zplane
        )
        return np.array(response, dtype=np.int32)

    def download_segmentation_image_file(self, mapobject_type_name,
            plate_name, well_name, well_pos_y, well_pos_x, tpoint, zplane,
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
            tpoint, zplane
        )
        image = np.array(response)
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
        content = {
            'plate_name': plate_name,
            'well_name': well_name,
            'well_pos_x': well_pos_x,
            'well_pos_y': well_pos_y,
            'tpoint': tpoint,
            'zplane': zplane,
            'image': image
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
        self._upload_segmentation_image(self, mapobject_type_name,
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
        if not filename.endswith('png'):
            raise IOError('Filename must have "png" extension.')
        filename = os.path.expanduser(os.path.exandvars(filename))
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

    def _download_object_feature_values(self, mapobject_type_name,
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

    def upload_feature_values(self, mapobject_type_name, plate_name,
            well_name, well_pos_y, well_pos_x, tpoint, data):
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
        data: pandas.DataFrame
            *n*x*p* dataframe, where *n* are number of objects at this site
            and *p* number of features (index must be site-specific one-based
            labels that must match those of the corresponding segmentation
            image)

        See also
        --------
        :func:`tmserver.api.feature.add_feature_values`
        :class:`tmlib.models.feature.FeatureValues`
        '''
        logger.info(
            'upload feature values for experiment "%s", object type "%s" at '
            'plate "%s", well "%s", y %d, x %d, tpoint %d',
            self.experiment_name, mapobject_type_name, plate_name, well_name,
            well_pos_y, well_pos_x, tpoint
        )
        content = {
            'metadata': {
                'plate_name': plate_name, 'well_name': well_name,
                'well_pos_y': well_pos_y, 'well_pos_x': well_pos_x,
                'tpoint': tpoint
            },
            'data': {
                'names': data.columns.tolist(),
                'labels': data.index.tolist(),
                'values': data.values.tolist()
            }
        }
        url = self._build_api_url(
            '/experiments/{experiment_id}/mapobject_types/{mapobject_type_id}/feature-values'.format(
                experiment_id=self._experiment_id,
                mapobject_type_id=mapobject_type_id
            )
        )
        res = self._session.post(url, json=content)
        res.raise_for_status()

    def download_object_feature_values(self, mapobject_type_name,
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
        res = self._download_object_feature_values(
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
            directory):
        '''Downloads all feature values for the given object type and stores the
        data as *CSV* files on disk.

        Parameters
        ----------
        mapobject_type_name: str
            type of the segmented objects
        directory: str
            absolute path to the directory on disk where the file should be

        See also
        --------
        :meth:`tmclient.api.TmClient.download_object_feature_values`
        :meth:`tmclient.api.TmClient.download_object_metadata`
        '''

        def download_per_well(well):
            logger.info(
                'download feature data at well: '
                'plate={plate}, well={well}'.format(
                    plate=well['plate_name'], well=well['name'],
                )
            )
            res = self._download_object_feature_values(
                mapobject_type_name, well['plate_name'], well['name']
            )
            filename = self._extract_filename_from_headers(res.headers)
            filepath = os.path.join(directory, filename)
            logger.info('write feature values to file: %s', filepath)
            with open(filepath, 'wb') as f:
                for c in res.iter_content(chunk_size=1000):
                    f.write(c)

            logger.info(
                'download feature metadata at well: '
                'plate={plate}, well={well}'.format(
                    plate=well['plate_name'], well=well['name'],
                )
            )
            res = self._download_object_metadata(
                mapobject_type_name, well['plate_name'], well['name']
            )
            filename = self._extract_filename_from_headers(res.headers)
            filepath = os.path.join(directory, filename)
            logger.info('write metadata to file: %s', filepath)
            with open(filepath, 'wb') as f:
                for c in res.iter_content(chunk_size=1000):
                    f.write(c)

        wells = self.get_wells()
        args = [(w, ) for w in wells]
        self._parallelize(download_per_well, args)
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
        if not filename.endswith('yml') and not filename.endswith('yaml'):
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

        def add_row_recursively(data, table, i):
            table.add_row([
                data['id'],
                data['name'],
                data['type'],
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
                add_row_recursively(subtd, table, i+1)

        t = PrettyTable([
                'ID', 'Name', 'Type', 'State', 'Done (%)', 'ExitCode',
                'Time (HH:MM:SS)', 'CPU Time (HH:MM:SS)', 'Memory (MB)'
        ])
        t.align['ID'] = 'l'
        t.align['Name'] = 'l'
        t.align['Type'] = 'l'
        t.align['State'] = 'l'
        t.align['Done (%)'] = 'r'
        t.align['Memory (MB)'] = 'r'
        t.padding_width = 1
        if status:
            add_row_recursively(status, t, 0)
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
