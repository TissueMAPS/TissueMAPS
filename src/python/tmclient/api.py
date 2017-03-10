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
import requests
import argparse
import os
import cgi
import re
import json
import cv2
import glob
import tempfile
import pandas as pd
import numpy as np
from cStringIO import StringIO
from prettytable import PrettyTable

from tmclient.base import HttpClient
from tmclient.log import configure_logging
from tmclient.log import map_logging_verbosity
from tmclient.errors import QueryError


logger = logging.getLogger(__name__)


class TmClient(HttpClient):

    '''Class for interacting with a *TissueMAPS* server via *RESTful API*.'''

    def __init__(self, host, port, experiment_name, user_name, password=None):
        '''
        Parameters
        ----------
        host: str
            name of the TissueMAPS host
        port: int
            number of the port to which TissueMAPS server listens
        experiment_name: str
            name of the experiment that should be queried
        user_name: str
            name of the TissueMAPS user
        password: str
            password for `username`
        '''
        super(TmClient, self).__init__(host, port, user_name, password)
        self.experiment_name = experiment_name

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
            raise AttributeError('Arguments must specify "method".')
        method_name = cli_args.method
        logger.debug('call method "%s"', method_name)
        if not hasattr(self, method_name):
            raise AttributeError(
                'Object of type "%s" doesn\'t have a method "%s"'
                % (self.__class__.__name__, method_name)
            )
        args = vars(cli_args)
        method = getattr(self, method_name)
        kwargs = dict()
        valid_arg_names = inspect.getargspec(method).args
        for arg_name, arg_value in args.iteritems():
            if arg_name in valid_arg_names:
                kwargs[arg_name] = arg_value
        method(**kwargs)

    @classmethod
    def __main__(cls):
        '''Main entry point for command line interface.'''
        parser = cls._get_parser()
        args = parser.parse_args()

        configure_logging()
        logging_level = map_logging_verbosity(args.verbosity)
        logging.getLogger('tmclient').setLevel(logging_level)
        logger.setLevel(logging_level)

        client = cls(
            args.host, args.port, args.experiment_name,
            args.user_name, args.password
        )
        client(args)

    @classmethod
    def _get_parser(cls):
        parser = argparse.ArgumentParser(
            prog='tm_client',
            description='TissueMAPS REST API client.'
        )
        parser.add_argument(
            '-H', '--host', required=True,
            help='name of TissueMAPS server host'
        )
        parser.add_argument(
            '-P', '--port', type=int, default=80,
            help='number of the port to which the server listens (default: 80)'
        )
        parser.add_argument(
            '-u', '--user', dest='user_name', required=True,
            help='name of TissueMAPS user'
        )
        parser.add_argument(
            '-p', '--password',
            help='password of TissueMAPS user'
        )
        parser.add_argument(
            '-v', '--verbosity', action='count', default=0,
            help='increase logging verbosity'
        )
        parser.add_argument(
            '-e', '--experiment', dest='experiment_name', required=True,
            help='name of the parent experiment'
        )

        subparsers = parser.add_subparsers(
            dest='resources', help='resources'
        )
        subparsers.required = True

        ###################
        # Abstract parser #
        ###################

        abstract_plate_parser = argparse.ArgumentParser(add_help=False)
        abstract_plate_parser.add_argument(
            '-p', '--plate', dest='plate_name', required=True,
            help='name of the plate'
        )

        abstract_well_parser = argparse.ArgumentParser(
            add_help=False, parents=[abstract_plate_parser]
        )
        abstract_well_parser.add_argument(
            '-w', '--well', dest='well_name', required=True,
            help='name of the well'
        )

        abstract_site_parser = argparse.ArgumentParser(
            add_help=False, parents=[abstract_well_parser]
        )
        abstract_site_parser.add_argument(
            '-x', dest='well_pos_x', type=int, required=True,
            help='zero-based x cooridinate of acquisition site within the well'
        )
        abstract_site_parser.add_argument(
            '-y', dest='well_pos_y', type=int, required=True,
            help='zero-based y cooridinate of acquisition site within the well'
        )

        abstract_acquisition_parser = argparse.ArgumentParser(
            add_help=False, parents=[abstract_plate_parser]
        )
        abstract_acquisition_parser.add_argument(
            '-a', '--acquisition', dest='acquisition_name', required=True,
            help='name of the acquisition'
        )

        abstract_site_parser = argparse.ArgumentParser(add_help=False)
        abstract_site_parser.add_argument(
            '-p', '--plate', dest='plate_name', required=True,
            help='name of the plate'
        )
        abstract_site_parser.add_argument(
            '-w', '--well', dest='well_name', required=True,
            help='name of the well'
        )
        abstract_site_parser.add_argument(
            '-x', '--well-pos-x', dest='well_pos_x', type=int, required=True,
            help='zero-based x cooridinate of acquisition site within the well'
        )
        abstract_site_parser.add_argument(
            '-y', '--well-pos-y', dest='well_pos_y', type=int, required=True,
            help='zero-based y cooridinate of acquisition site within the well'
        )

        abstract_tpoint_parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        abstract_tpoint_parser.add_argument(
            '-t', '--tpoint', type=int, default=0,
            help='zero-based time point index'
        )

        abstract_zplane_parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        abstract_zplane_parser.add_argument(
            '-z', '--zplane', type=int, default=0,
            help='zero-based z-plane index'
        )

        abstract_object_parser = argparse.ArgumentParser(add_help=False)
        abstract_object_parser.add_argument(
            '-o', '--object-type', dest='mapobject_type_name', required=True,
            help='name of the objects type'
        )

        abstract_feature_parser = argparse.ArgumentParser(add_help=False)
        abstract_feature_parser.add_argument(
            '-f', '--feature', dest='feature_name', required=True,
            help='name of the feature'
        )

        abstract_channel_parser = argparse.ArgumentParser(add_help=False)
        abstract_channel_parser.add_argument(
            '-c', '--channel', dest='channel_name', required=True,
            help='name of the channel'
        )

        abstract_name_parser = argparse.ArgumentParser(add_help=False)
        abstract_name_parser.add_argument(
            '-n', '--name', required=True, help='name'
        )

        abstract_new_name_parser = argparse.ArgumentParser(add_help=False)
        abstract_new_name_parser.add_argument(
            '--new-name', dest='new_name', required=True, help='new name'
        )

        abstract_description_parser = argparse.ArgumentParser(add_help=False)
        abstract_description_parser.add_argument(
            '--description', default='', help='optional description'
        )

        ############
        # Workflow #
        ############

        workflow_parser = subparsers.add_parser(
            'workflow', help='workflow resources',
            description='Access workflow resources of the experiment.'
        )
        workflow_subparsers = workflow_parser.add_subparsers(
            dest='workflow_methods', help='access methods'
        )
        workflow_subparsers.required = True

        data_parser = subparsers.add_parser(
            'data', help='data resources',
            description='Access data resources of the experiment.'
        )
        data_subparsers = data_parser.add_subparsers(
            dest='data_models', help='data resource type'
        )
        data_subparsers.required = True


        ##############
        # Experiment #
        ##############

        experiment_parser = data_subparsers.add_parser(
            'experiment', help='experiment resources',
            description='Access experiment resources.',
        )
        experiment_subparsers = experiment_parser.add_subparsers(
            dest='experiment_methods', help='access methods'
        )
        experiment_subparsers.required = True

        experiment_rename_parser = experiment_subparsers.add_parser(
            'rename', help='rename the experiment',
            description='Rename the experiment.',
            parents=[abstract_new_name_parser]
        )
        experiment_rename_parser.set_defaults(method='rename_experiment')

        experiment_create_parser = experiment_subparsers.add_parser(
            'create', help='create the experiment',
            description='Create the experiment.',
        )
        experiment_create_parser.add_argument(
            '--microscope-type', dest='microscope_type',
            default='cellvoyager', help='microscope type'
        )
        experiment_create_parser.add_argument(
            '--plate-format', dest='plate_format',
            type=int, default=384,
            help='well-plate format, i.e. total number of wells per plate'
        )
        experiment_create_parser.add_argument(
            '--plate-acquisition-mode', dest='plate_acquisition_mode',
            default='basic', choices={'basic', 'multiplexing'},
            help='''
                whether multiple acquisitions of the same plate are interpreted
                as time points ("basic" mode) or multiplexing cycles
                ("multiplexing" mode)
            '''
        )
        experiment_create_parser.set_defaults(method='create_experiment')

        experiment_delete_parser = experiment_subparsers.add_parser(
            'rm', help='delete the experiment',
            description='Delete the experiment.',
        )
        experiment_delete_parser.set_defaults(method='delete_experiment')


        ##########
        # Plates #
        ##########

        plate_parser = data_subparsers.add_parser(
            'plate', help='plate resources',
            description='Access plate resources.',
        )
        plate_subparsers = plate_parser.add_subparsers(
            dest='plate_methods', help='access methods'
        )
        plate_subparsers.required = True

        plate_list_parser = plate_subparsers.add_parser(
            'ls', help='list plates',
            description='List plates.'
        )
        plate_list_parser.set_defaults(method='_list_plates')

        plate_rename_parser = plate_subparsers.add_parser(
            'rename', help='rename a plate',
            description='Rename a plate.',
            parents=[abstract_name_parser, abstract_new_name_parser]
        )
        plate_rename_parser.set_defaults(method='rename_plate')

        plate_create_parser = plate_subparsers.add_parser(
            'create', help='create a new plate',
            description='Create a new plate.',
            parents=[abstract_name_parser, abstract_description_parser]
        )
        plate_create_parser.set_defaults(method='create_plate')

        plate_delete_parser = plate_subparsers.add_parser(
            'rm', help='delete a plate',
            description='Delete a plate.',
            parents=[abstract_name_parser]
        )
        plate_delete_parser.set_defaults(method='delete_plate')


        #########
        # Wells #
        #########

        well_parser = data_subparsers.add_parser(
            'well', help='well resources',
            description='Access well resources.',
        )
        well_subparsers = well_parser.add_subparsers(
            dest='well_methods', help='access methods'
        )
        well_subparsers.required = True

        well_list_parser = well_subparsers.add_parser(
            'ls', help='list wells',
            description='List wells.'
        )
        well_list_parser.set_defaults(method='_list_wells')


        #########
        # Sites #
        #########

        site_parser = data_subparsers.add_parser(
            'site', help='site resources',
            description='Access site resources.',
        )
        site_subparsers = site_parser.add_subparsers(
            dest='site_methods', help='access methods'
        )
        site_subparsers.required = True

        site_list_parser = site_subparsers.add_parser(
            'ls', help='list sites',
            description='List sites.'
        )
        site_list_parser.set_defaults(method='_list_sites')


        ###############
        # Acquistions #
        ###############

        acquisition_parser = data_subparsers.add_parser(
            'acquisition', help='acquisition resources',
            description='Access acquisition resources.',
        )
        acquisition_subparsers = acquisition_parser.add_subparsers(
            dest='acquisition_methods', help='access methods'
        )
        acquisition_subparsers.required = True

        acquisition_list_parser = acquisition_subparsers.add_parser(
            'ls', help='list acquisitions',
            description='List acquisitions.',
            parents=[abstract_plate_parser]
        )
        acquisition_list_parser.set_defaults(method='_list_acquisitions')

        acquisition_create_parser = acquisition_subparsers.add_parser(
            'create', help='create an acquisition',
            description='Create a new acquisition for an existing plate.',
            parents=[
                abstract_name_parser, abstract_plate_parser,
                abstract_description_parser
            ]
        )
        acquisition_create_parser.set_defaults(method='create_acquisition')

        acquisition_delete_parser = acquisition_subparsers.add_parser(
            'rm', help='delete an acquisition',
            description='Delete an acquisition.',
            parents=[abstract_name_parser, abstract_plate_parser]
        )
        acquisition_delete_parser.set_defaults(method='delete_acquisition')

        acquisition_rename_parser = acquisition_subparsers.add_parser(
            'rename', help='rename an acquisition',
            description='Rename an acquisition.',
            parents=[
                abstract_name_parser, abstract_plate_parser,
                abstract_new_name_parser
            ]
        )
        acquisition_rename_parser.set_defaults(method='rename_acquisition')


        ####################
        # Microscope files #
        ####################

        microscope_file_parser = data_subparsers.add_parser(
            'microscope-file', help='microscope file resources',
            description='Access microscope file resources.',
        )
        microscope_file_subparsers = microscope_file_parser.add_subparsers(
            dest='microscope_file_methods', help='access methods'
        )
        microscope_file_subparsers.required = True

        microscope_file_list_parser = microscope_file_subparsers.add_parser(
            'ls', help='list microscope files',
            description='List microscope files.',
            parents=[abstract_acquisition_parser]
        )
        microscope_file_list_parser.set_defaults(method='_list_microscope_files')

        microscope_file_upload_parser = microscope_file_subparsers.add_parser(
            'upload',
            help='upload microscope files',
            description='Upload microscope image and metadata files.',
            parents=[abstract_acquisition_parser]
        )
        microscope_file_upload_parser.add_argument(
            '--directory', required=True,
            help='path to directory where files are located'
        )
        microscope_file_upload_parser.set_defaults(
            method='upload_microscope_files'
        )


        ############
        # Channels #
        ############

        channel_parser = data_subparsers.add_parser(
            'channel', help='channel resources',
            description='Access channel resources.',
        )
        channel_subparsers = channel_parser.add_subparsers(
            dest='channel_methods', help='access methods'
        )
        channel_subparsers.required = True

        channel_list_parser = channel_subparsers.add_parser(
            'ls', help='list channels',
            description='List channels.',
        )
        channel_list_parser.set_defaults(method='_list_channels')

        channel_rename_parser = channel_subparsers.add_parser(
            'rename', help='rename a channel',
            description='Rename a channel.',
            parents=[abstract_name_parser, abstract_new_name_parser]
        )
        channel_rename_parser.set_defaults(method='rename_channel')


        ###################
        # Mapobject types #
        ###################

        object_type_parser = data_subparsers.add_parser(
            'object-type', help='object type resources',
            description='Access object type resources.',
        )
        object_type_subparsers = object_type_parser.add_subparsers(
            dest='object_type_methods', help='access methods'
        )
        object_type_subparsers.required = True

        object_type_list_parser = object_type_subparsers.add_parser(
            'ls', help='list object types',
            description='List object types.',
        )
        object_type_list_parser.set_defaults(method='_list_mapobject_types')

        object_type_rename_parser = object_type_subparsers.add_parser(
            'rename', help='rename an object type',
            description='Rename an object type.',
            parents=[abstract_name_parser, abstract_new_name_parser]
        )
        object_type_rename_parser.set_defaults(method='rename_mapobject_type')

        object_type_delete_parser = object_type_subparsers.add_parser(
            'rm', help='delete an objects type',
            description='Delete an objects type.',
            parents=[abstract_name_parser]
        )
        object_type_delete_parser.set_defaults(method='delete_mapobjects_type')


        ############
        # Features #
        ############

        feature_parser = data_subparsers.add_parser(
            'feature', help='feature resources',
            description='Access feature resources.',
        )
        feature_subparsers = feature_parser.add_subparsers(
            dest='feature_methods', help='access methods'
        )
        feature_subparsers.required = True

        feature_list_parser = feature_subparsers.add_parser(
            'ls', help='list features',
            description='List features for a given object type.',
            parents=[abstract_object_parser]
        )
        feature_list_parser.set_defaults(method='_list_features')

        feature_rename_parser = feature_subparsers.add_parser(
            'rename', help='rename a feature',
            description='Rename a feature.',
            parents=[
                abstract_name_parser, abstract_object_parser,
                abstract_new_name_parser
            ]
        )
        feature_rename_parser.set_defaults(method='rename_feature')

        feature_delete_parser = feature_subparsers.add_parser(
            'rm', help='delete a feature',
            description='Delete a feature.',
            parents=[abstract_name_parser, abstract_object_parser]
        )
        feature_delete_parser.set_defaults(method='delete_feature')


        ##################
        # Feature values #
        ##################

        feature_values_parser = data_subparsers.add_parser(
            'feature-values', help='feature values resources',
            description='Access feature values resources.',
        )
        feature_values_subparsers = feature_values_parser.add_subparsers(
            dest='feature_values_methods', help='access methods'
        )
        feature_values_subparsers.required = True

        feature_value_download_parser = feature_values_subparsers.add_parser(
            'download', help='download feature values for segmented objects',
            description='''
                Download feature values for segmented objects as well as the
                corresponding metadata.
            ''',
            parents=[abstract_object_parser],
        )
        feature_value_download_parser.set_defaults(
            method='download_feature_values_and_metadata_files'
        )


        ###########################
        # Mapobject segmentations #
        ###########################

        segmentation_parser = data_subparsers.add_parser(
            'segmentation', help='segmentation resources',
            description='Access segmentation resources.',
        )
        segmentation_subparsers = segmentation_parser.add_subparsers(
            dest='segmentation_methods', help='access methods'
        )
        segmentation_subparsers.required = True

        segmentation_upload_parser = segmentation_subparsers.add_parser(
            'upload',
            help='upload segmenations from image file',
            description='''
                Upload object segmentations in from a 16-bit PNG image file.
                The image must be labeled such that background pixels have zero
                values and pixels within objects have unsigned integer values.

                WARNING: This approach only works when the image contains less
                than 65536 objects.
            ''',
            parents=[
                abstract_site_parser, abstract_tpoint_parser,
                abstract_zplane_parser, abstract_object_parser
            ]
        )
        segmentation_upload_parser.add_argument(
            '--filename', required=True, help='path to the file on disk'
        )
        segmentation_upload_parser.set_defaults(
            method='upload_segmentation_image_file'
        )

        segmentation_download_parser = segmentation_subparsers.add_parser(
            'segmentation-image-file',
            help='download segmented objects as label image',
            description='''
                Download segmentations in form of a 16-bit PNG image file.

                WARNING: This approach only works when the image contains less
                than 65536 objects.
            ''',
            parents=[
                abstract_site_parser, abstract_tpoint_parser,
                abstract_zplane_parser, abstract_object_parser
            ]
        )
        segmentation_download_parser.add_argument(
            '--directory',
            help='''
                path to directory where file should be stored
                (defaults to temporary directory)
            '''
        )
        segmentation_download_parser.set_defaults(
            method='download_segmentation_image_file'
        )

        #######################
        # Channel image files #
        #######################

        channel_image_parser = data_subparsers.add_parser(
            'channel-image', help='channel image resources',
            description='Access channel image resources.',
        )
        channel_image_subparsers = channel_image_parser.add_subparsers(
            dest='channel_image_methods', help='access methods'
        )
        channel_image_subparsers.required = True

        channel_image_download_parser = channel_image_subparsers.add_parser(
            'download', help='download channel image',
            description='Download channel image to PNG file.',
            parents=[
                abstract_site_parser, abstract_tpoint_parser,
                abstract_zplane_parser, abstract_channel_parser
            ]
        )
        channel_image_download_parser.set_defaults(
            method='download_channel_image_file'
        )
        channel_image_download_parser.add_argument(
            '-i', '--cycle-index', dest='cycle_index', default=0,
            help='zero-based index of the cycle'
        )
        channel_image_download_parser.add_argument(
            '--correct', action='store_true',
            help='whether image should be corrected for illumination artifacts'
        )
        channel_image_download_parser.add_argument(
            '--directory',
            help='''
                path to directory where file should be stored
                (defaults to temporary directory)
            '''
        )

        return parser

    @property
    def _experiment_id(self):
        '''str: ID of an existing experiment'''
        logger.debug('get ID for experiment "%s"', self.experiment_name)
        params = {'name': self.experiment_name}
        url = self._build_url('/api/experiments', params)
        res = self._session.get(url)
        res.raise_for_status()
        data = res.json()['data']
        if len(data) > 1:
            raise QueryError(
                'More than one experiment found with name "%s"' %
                experiment_name
            )
        if len(data) == 0:
            raise QueryError(
                'Experiment "%s" does not exist.' % experiment_name
            )
        return data[0]['id']

    def create_experiment(self, microscope_type, plate_format,
            plate_acquisition_mode):
        '''Creates a new experiment.

        Parameters
        ----------
        microscope_type: str
            microscope_type
        plate_format: int
            well-plate format, i.e. total number of wells per plate
        plate_acquisition_mode: str
            mode of image acquisition that determines whether acquisitions will
            be interpreted as time points as part of a time series experiment
            or as multiplexing cycles as part of a serial multiplexing
            experiment

        See also
        --------
        :class:`tmserver.api.experiment.create_experiment`
        :class:`tmlib.models.experiment.ExperimentReference`
        :class:`tmlib.models.experiment.Experiment`
        '''
        logger.info('create experiment "%s"', self.experiment_name)
        content = {
            'name': self.experiment_name,
            'microscope_type': microscope_type,
            'plate_format': plate_format,
            'plate_acquisition_mode': plate_acquisition_mode
        }
        url = self._build_url('/api/experiments')
        res = self._session.post(url, json=content)
        res.raise_for_status()

    def rename_experiment(self, new_name):
        '''Renames an experiment.

        See also
        --------
        :class:`tmserver.api.experiment.rename_experiment`
        :class:`tmlib.models.experiment.ExperimentReference`
        '''
        logger.info('rename experiment "%s"', self.experiment_name)
        content = {'name': new_name}
        url = self._build_url(
            '/api/experiments/{experiment_id}'.format(
                experiment_id=self._experiment_id
            )
        )
        res = self._session.put(url, json=content)
        res.raise_for_status()

    def delete_experiment(self):
        '''Deletes an experiment.

        See also
        --------
        :class:`tmserver.api.experiment.delete_experiment`
        :class:`tmlib.models.experiment.ExperimentReference`
        :class:`tmlib.models.experiment.Experiment`
        '''
        logger.info('delete experiment "%s"', self.experiment_name)
        url = self._build_url(
            '/api/experiments/{experiment_id}'.format(
                experiment_id=self._experiment_id
            )
        )
        res = self._session.delete(url)
        res.raise_for_status()

    def _get_plate_id(self, name):
        '''Gets the ID of an existing plate given its name.

        Parameters
        ----------
        name: str
            name of the plate

        Returns
        -------
        str
            plate ID

        '''
        logger.debug(
            'get plate ID for experiment "%s", plate "%s"',
            self.experiment_name, name
        )
        params = {
            'name': name,
        }
        url = self._build_url(
            '/api/experiments/{experiment_id}/plates'.format(
                experiment_id=self._experiment_id
            ),
            params
        )
        res = self._session.get(url)
        res.raise_for_status()
        data = res.json()['data']
        if len(data) > 1:
            raise QueryError(
                'More than one plate found with name "{0}"'.format(name)
            )
        elif len(data) == 0:
            raise QueryError(
                'No plate found with name "{0}"'.format(name)
            )
        return data[0]['id']

    def create_plate(self, name, description):
        '''Creates a new plate.

        Parameters
        ----------
        name: str
            name that should be given to the plate
        description: str, optional
            description of the plate

        See also
        --------
        :class:`tmserver.api.experiment.create_plate`
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
        url = self._build_url(
            '/api/experiments/{experiment_id}/plates'.format(
                experiment_id=self._experiment_id
            )
        )
        res = self._session.post(url, json=content)
        res.raise_for_status()

    def delete_plate(self, name):
        '''Deletes a plate.

        Parameters
        ----------
        name: str
            name of the plate that should be deleted

        See also
        --------
        :class:`tmserver.api.experiment.delete_plate`
        :class:`tmlib.models.plate.Plate`
        '''
        logger.info(
            'delete plate "%s" of experiment "%s"',
            name, self.experiment_name
        )
        plate_id = self._get_plate_id(name)
        url = self._build_url(
            '/api/experiments/{experiment_id}/plates/{plate_id}'.format(
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
        :class:`tmserver.api.experiment.rename_plate`
        :class:`tmlib.models.plate.Plate`
        '''
        logger.info(
            'rename plate "%s" of experiment "%s"',
            name, self.experiment_name
        )
        plate_id = self._get_plate_id(name)
        content = {'name': new_name}
        url = self._build_url(
            '/api/experiments/{experiment_id}/plates/{plate_id}'.format(
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
        :func:`tmserver.api.experiment.get_plates`
        :class:`tmlib.models.plate.Plate`
        '''
        logger.info('get plates of experiment "%s"', self.experiment_name)
        url = self._build_url(
            '/api/experiments/{experiment_id}/plates'.format(
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
        url = self._build_url(
            '/api/experiments/{experiment_id}/acquisitions'.format(
                experiment_id=self._experiment_id
            ),
            params
        )
        res = self._session.get(url)
        res.raise_for_status()
        data = res.json()['data']
        if len(data) > 1:
            raise QueryError(
                'More than one acquisition found with name "{0}" and '
                'plate name "{1}".'.format(name, plate_name)
            )
        elif len(data) == 0:
            raise QueryError(
                'No acquisition found with name "{0}" and '
                'plate name "{1}".'.format(name, plate_name)
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

        See also
        --------
        :class:`tmserver.api.experiment.create_acquisition`
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
        url = self._build_url(
            '/api/experiments/{experiment_id}/acquisitions'.format(
                experiment_id=self._experiment_id
            )
        )
        res = self._session.post(url, json=content)
        res.raise_for_status()

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
        :class:`tmserver.api.experiment.rename_acquisition`
        :class:`tmlib.models.acquisition.Acquisition`
        '''
        logger.info(
            'rename acquisistion "%s" of experiment "%s", plate "%s"',
            name, self.experiment_name, plate_name
        )
        content = {'name': new_name}
        acquisition_id = self._get_acquisition_id(plate_name, name)
        url = self._build_url(
            '/api/experiments/{experiment_id}/acquisitions/{acquisition_id}'.format(
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
        :class:`tmserver.api.experiment.delete_acquisition`
        :class:`tmlib.models.acquisition.Acquisition`
        '''
        logger.info(
            'delete acquisition "%s" of experiment "%s", plate "%s"',
            name, self.experiment_name, plate_name
        )
        acquisition_id = self._get_acquisition_id(plate_name, name)
        url = self._build_url(
            '/api/experiments/{experiment_id}/acquisitions/{acquisition_id}'.format(
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
            id, name, status and description for each acquisition

        See also
        --------
        :func:`tmserver.api.experiment.get_acquisitions`
        :class:`tmlib.models.acquisition.Acquisition`
        '''
        logger.info('get acquisitions of experiment "%s"', self.experiment_name)
        params = dict()
        if plate_name is not None:
            logger.info('filter acquisitions for plate "%s"', plate_name)
            params['plate_name'] = plate_name
        url = self._build_url(
            '/api/experiments/{experiment_id}/acquisitions'.format(
                experiment_id=self._experiment_id
            ),
            params
        )
        res = self._session.get(url)
        res.raise_for_status()
        return res.json()['data']

    def _list_acquisitions(self, plate_name=None):
        acquisitions = self.get_acquisitions(plate_name)
        t = PrettyTable(['ID', 'Status', 'Name', 'Description'])
        t.padding_width = 1
        for a in acquisitions:
            t.add_row([a['id'], a['status'], a['name'], a['description']])
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
        url = self._build_url(
            '/api/experiments/{experiment_id}/wells'.format(
                experiment_id=self._experiment_id
            ),
            params
        )
        res = self._session.get(url)
        res.raise_for_status()
        data = res.json()['data']
        if len(data) > 1:
            raise QueryError(
                'More than one well found with name "{0}" for '
                'plate "{1}".'.format(name, plate_name)
            )
        elif len(data) == 0:
            raise QueryError(
                'No well found with name "{0}" for plate "{1}".'.format(
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
        :func:`tmserver.api.experiment.get_wells`
        :class:`tmlib.models.well.Well`
        '''
        logger.info('get wells of experiment "%s"', self.experiment_name)
        params = dict()
        if plate_name is not None:
            logger.info('filter wells for plate "%s"', plate_name)
            params['plate_name'] = plate_name
        url = self._build_url(
            '/api/experiments/{experiment_id}/wells'.format(
                experiment_id=self._experiment_id
            ),
            params
        )
        res = self._session.get(url)
        res.raise_for_status()
        return res.json()['data']

    def _list_wells(self, plate_name=None):
        wells = self.get_wells(plate_name)
        t = PrettyTable(['ID', 'Name', 'Description'])
        t.padding_width = 1
        for w in wells:
            t.add_row([w['id'], w['name'], w['description']])
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
        url = self._build_url(
            '/api/experiments/{experiment_id}/sites'.format(
                experiment_id=self._experiment_id
            ),
            params
        )
        res = self._session.get(url)
        res.raise_for_status()
        data = res.json()['data']
        if len(data) > 1:
            raise QueryError(
                'More than one site found at y %d, x %d for well "{0}" and '
                'plate "{1}".'.format(
                    well_pos_y, well_pos_x, well_name, plate_name
                )
            )
        elif len(data) == 0:
            raise QueryError(
                'No site found at y %d, x %d for well "{0}" and '
                'plate "{1}".'.format(
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
        :func:`tmserver.api.experiment.get_wells`
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
        url = self._build_url(
            '/api/experiments/{experiment_id}/wells'.format(
                experiment_id=self._experiment_id
            ),
            params
        )
        res = self._session.get(url)
        res.raise_for_status()
        return res.json()['data']

    def _list_sites(self, plate_name=None, well_name=None):
        wells = self.get_wells(plate_name)
        t = PrettyTable(['ID', 'Name', 'Description'])
        t.padding_width = 1
        for w in wells:
            t.add_row([w['id'], w['name'], w['description']])
        print(t)

    def _get_mapobject_type_id(self, name):
        logger.debug(
            'get mapobject type ID for experiment "%s" and mapobjec type "%s"',
            self.experiment_name, name
        )
        params = {'name': name}
        url = self._build_url(
            '/api/experiments/{experiment_id}/mapobject_types'.format(
                experiment_id=self._experiment_id
            ),
            params
        )
        res = self._session.get(url)
        res.raise_for_status()
        data = res.json()['data']
        if len(data) > 1:
            raise QueryError(
                'More than one mapobject type found with name "{0}".'.format(
                    name
                )
            )
        elif len(data) == 0:
            raise QueryError(
                'No mapobject type found with name "{0}".'.format(name)
            )
        return data[0]['id']

    def _get_feature_id(self, name):
        logger.debug(
            'get feature ID for experiment "%s" and feature "%s"',
            self.experiment_name, name
        )
        params = {'name': name}
        url = self._build_url(
            '/api/experiments/{experiment_id}/features'.format(
                experiment_id=self._experiment_id
            ),
            params
        )
        res = self._session.get(url)
        res.raise_for_status()
        data = res.json()['data']
        if len(data) > 1:
            raise QueryError(
                'More than one feature found with name "{0}".'.format(name)
            )
        elif len(data) == 0:
            raise QueryError(
                'No feature found with name "{0}".'.format(name)
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
        url = self._build_url(
            '/api/experiments/{experiment_id}/cycles'.format(
                experiment_id=self._experiment_id
            ),
            params
        )
        res = self._session.get(url)
        res.raise_for_status()
        data = res.json()['data']
        if len(data) > 1:
            raise QueryError(
                'More than one cycle found with index {0} and '
                'plate name "{1}".'.format(index, plate_name)
            )
        elif len(data) == 0:
            raise QueryError(
                'No cycle found with index {0} and '
                'plate name "{1}".'.format(cycle_index, plate_name)
            )
        return data[0]['id']

    def _get_channel_id(self, name):
        logger.debug(
            'get channel ID for experiment "%s" and channel "%s"',
            self.experiment_name, name
        )
        params = {'name': name}
        url = self._build_url(
            '/api/experiments/{experiment_id}/channels'.format(
                experiment_id=self._experiment_id
            ),
            params
        )
        res = self._session.get(url)
        res.raise_for_status()
        data = res.json()['data']
        if len(data) > 1:
            raise QueryError(
                'More than one channel found with name "{0}".'.format(name)
            )
        elif len(data) == 0:
            raise QueryError(
                'No channel found with name "{0}".'.format(name)
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
        url = self._build_url(
            '/api/experiments/{experiment_id}/channel_layers'.format(
                experiment_id=self._experiment_id
            ),
            params
        )
        res = self._session.get(url)
        res.raise_for_status()
        data = res.json()['data']
        if len(data) > 1:
            raise QueryError(
                'More than one channel layer found for experiment "{0}", '
                'channel "{1}", tpoint {2} and zplane {3}.'.format(
                    self.experiment_name, channel_name, tpoint, zplane
                )
            )
        elif len(data) == 0:
            raise QueryError(
                'No channel layer found for experiment "{0}", channel "{1}", '
                'tpoint {2} and zplane {3}.'.format(
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
        :func:`tmserver.api.experiment.get_microscope_image_files`
        :func:`tmserver.api.experiment.get_microscope_metadata_files`
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
        logger.debug('get image files for acquisition %d', acquisition_id)
        url = self._build_url(
            '/api/experiments/{experiment_id}/acquisitions/{acquisition_id}/images'.format(
                experiment_id=self._experiment_id, acquisition_id=acquisition_id
            )
        )
        res = self._session.get(url)
        res.raise_for_status()
        return res.json()['data']

    def _get_metadata_files(self, acquisition_id):
        logger.debug(
            'get metadata files for experiment "%s" and acquisition %d',
            self.experiment_name, acquisition_id
        )
        url = self._build_url(
            '/api/experiments/{experiment_id}/acquisitions/{acquisition_id}/metadata'.format(
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

        See also
        --------
        :func:`tmserver.api.upload.register_upload`
        :func:`tmserver.api.upload.upload_file`
        :class:`tmlib.models.file.MicroscopeImageFile`
        :class:`tmlib.models.file.MicroscopeMetadataFile`
        '''
        # TODO: consider using os.walk() to screen subdirectories recursively
        logger.info(
            'upload microscope files for experiment "%s", plate "%s" '
            'and acquisition "%s"',
            self.experiment_name, plate_name, acquisition_name
        )
        directory = os.path.expanduser(directory)
        directory = os.path.expandvars(directory)
        filenames = os.listdir(directory)
        acquisition_id = self._get_acquisition_id(plate_name, acquisition_name)
        registered_filenames = self._register_files_for_upload(
            acquisition_id, filenames
        )
        for name in filenames:
            logger.info('upload file: %s', name)
            filepath = os.path.join(directory, name)
            self._upload_file(acquisition_id, filepath)

    def _register_files_for_upload(self, acquisition_id, filenames):
        '''Registers microscope files for upload.

        Parameters
        ----------
        acquisition_id: str
            ID of the acquisition
        filenames: List[str]
            names of files that should be uploaded

        Returns
        -------
        List[str]
            names of valid files that have been registered
        '''
        logger.debug(
            'register files for upload of experiment %d, acquisition %d',
            self._experiment_id, acquisition_id
        )
        url = self._build_url(
            '/api/experiments/{experiment_id}/acquisitions/{acquisition_id}/upload/register'.format(
                experiment_id=self._experiment_id, acquisition_id=acquisition_id
            )
        )
        payload = {'files': filenames}
        res = self._session.post(url, json=payload)
        res.raise_for_status()
        return res.json()['data']

    def _upload_file(self, acquisition_id, filepath):
        '''Uploads an individual file.

        Parameters
        ----------
        acquisition_id: str
            ID of the acquisition
        filepath: str
            absolute path to the file on the local disk
        '''
        logger.debug(
            'upload file "%s" for experiment %d, acquisition %d', filepath,
            self._experiment_id, acquisition_id
        )
        url = self._build_url(
            '/api/experiments/{experiment_id}/acquisitions/{acquisition_id}/microscope-file'.format(
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
        if directory is None:
            directory = tempfile.gettempdir()
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
            'well_pox_y': well_pos_y,
            'tpoint': tpoint,
            'zplane': zplane,
            'correct': correct
        }
        url = self._build_url(
            '/api/experiments/{experiment_id}/channels/{channel_name}/image-file'.format(
                experiment_id=self._experiment_id, channel_name=channel_id
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
        :class:`tmserver.api.experiment.rename_channel`
        :class:`tmlib.models.channel.Channel`
        '''
        logger.info(
            'rename channel "%s" of experiment "%s"',
            name, self.experiment_name
        )
        channel_id = self._get_channel_id(name)
        content = {'name': new_name}
        url = self._build_url(
            '/api/experiments/{experiment_id}/channels/{channel_id}'.format(
                experiment_id=self._experiment_id, channel_id=channel_id
            )
        )
        res = self._session.put(url, json=content)
        res.raise_for_status()

    def get_channels(self):
        '''Gets channels.

        Returns
        -------
        List[Dict[str, str]]
            information about each channel

        See also
        --------
        :func:`tmserver.api.experiment.get_channels`
        :class:`tmlib.models.channel.Channel`
        '''
        logger.info('get channels of experiment "%s"', self.experiment_name)
        url = self._build_url(
            '/api/experiments/{experiment_id}/channels'.format(
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
        :func:`tmserver.api.experiment.get_channel_image`
        :class:`tmlib.models.file.ChannelImageFile`
        :class:`tmlib.image.ChannelImage`
        '''
        response = self._download_channel_image(
            channel_name, plate_name, well_name, well_pos_y, well_pos_x,
            cycle_index=cycle_index, tpoint=tpoint, zplane=zplane,
            correct=correct
        )
        data = np.frombuffer(response.content, np.uint8)
        return cv2.imdecode(data, cv2.IMREAD_UNCHANGED)

    def download_channel_image_file(self, channel_name, plate_name,
            well_name, well_pos_y, well_pos_x, cycle_index=0,
            tpoint=0, zplane=0, correct=True, directory=None):
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
        cycle_index: str, optional
            zero-based cycle index (default: ``0``)
        tpoint: int, optional
            zero-based time point index (default: ``0``)
        zplane: int, optional
            zero-based z-plane index (default: ``0``)
        correct: bool, optional
            whether image should be corrected for illumination artifacts
            (default: ``True``)
        directory: str, optional
            absolute path to the directory on disk where the file should be saved
            (defaults to temporary directory)

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
            well_pox_y, well_pos_x, tpoint, zplane
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
        url = self._build_url(
            '/api/experiments/{experiment_id}/mapobject_types/{mapobject_type_id}/segmentation-image-file'.format(
                experiment_id=self._experiment_id,
                mapobject_type_id=mapobject_type_id
            ),
            params
        )
        response = self._session.get(url)
        response.raise_for_status()
        return response

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
        numpy.ndarray[numpy.uint16]
            labeled image where each label encodes a segmented object

        Warning
        -------
        Due to the *PNG* encoding this approach is limited to images
        with less than 65536 segmented objects.

        See also
        --------
        :func:`tmserver.api.experiment.get_segmentation_image`
        :class:`tmlib.models.mapobject.MapobjectSegmentation`
        :class:`tmlib.image.SegmentationImage`
        '''
        response = self._download_segmentation_image(
            mapobject_type_name, plate_name, well_name, well_pos_y, well_pos_x,
            tpoint=0, zplane=0
        )
        data = np.frombuffer(response.content, np.uint16)
        pixels = cv2.imdecode(data, cv2.IMREAD_UNCHANGED | cv2.IMREAD_ANYDEPTH)
        return pixels.astype(np.uint16)

    def download_segmentation_image_file(self, mapobject_type_name,
            plate_name, well_name, well_pos_y, well_pos_x, tpoint=0, zplane=0,
            directory=None):
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
        tpoint: int, optional
            zero-based time point index (default: ``0``)
        zplane: int, optional
            zero-based z-plane index (default: ``0``)
        directory: str, optional
            absolute path to the directory on disk where the file should be saved
            (defaults to temporary directory)

        See also
        --------
        :meth:`tmclient.api.TmClient.download_segmentation_image`
        '''
        response = self._download_segmentation_image(
            mapobject_type_name, plate_name, well_name, well_pos_y, well_pos_x,
            tpoint=0, zplane=0
        )
        data = response.content
        filename = self._extract_filename_from_headers(response.headers)
        self._write_file(directory, filename, data)

    def _upload_segmentation_image(self, mapobject_type_name,
            plate_name, well_name, well_pos_y, well_pos_x, tpoint, zplane,
            pixels):
        logger.info(
            'upload segmentation image for experiment "%s", objects "%s" at '
            'plate "%s", well "%s", y %d, x %d, tpoint %d, zplane %d',
            self.experiment_name, mapobject_type_name, plate_name, well_name,
            well_pox_y, well_pos_x, tpoint, zplane
        )
        content = {
            'plate_name': plate_name,
            'well_name': well_name,
            'well_pos_x': well_pos_x,
            'well_pos_y': well_pos_y,
            'tpoint': tpoint,
            'zplane': zplane,
            'pixels': pixels
        }
        mapobject_type_id = self._get_mapobject_type_id(mapobject_type_name)
        url = self._build_url(
            '/api/experiments/{experiment_id}/mapobject_types/{mapobject_type_id}/segmentation-image-file'.format(
                experiment_id=self._experiment_id,
                mapobject_type_id=mapobject_type_id
            )
        )
        response = self._session.post(url, json=content)
        response.raise_for_status()

    def upload_segmentation_image(self, mapobject_type_name,
            plate_name, well_name, well_pos_y, well_pos_x, tpoint, zplane,
            image):
        '''Uploads a segmentation image from a file on disk.

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
        image: numpy.ndarray[numpy.uint16]
            labeled array
        '''
        if image.dtype != np.uint16:
            raise ValueError(
                'Argument "image" must have numpy.uint16 data type.'
            )
        pixels = cv2.imencode('.png', image)[1]
        _upload_segmentation_image(self, mapobject_type_name,
            plate_name, well_name, well_pos_y, well_pos_x, tpoint, zplane,
            pixels
        )

    def upload_segmentation_image_file(self, mapobject_type_name,
            plate_name, well_name, well_pos_y, well_pos_x, tpoint, zplane,
            filename):
        '''Uploads a segmentation image from a file on disk.

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
            absolute path to *PNG* file on disk
        '''
        logger.info('upload segmentation image file "%s"', filename)
        if not filename.endswith('png'):
            raise IOError('Filename must have "png" extension.')
        with open(filename, 'rb') as f:
            pixels = f.read()
        self._upload_segmentation_image(
            mapobject_type_name, plate_name, well_name, well_pos_y, well_pos_x,
            tpoint, zplane, pixels
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
        :func:`tmserver.api.mapobject.rename_feature`
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
        url = self._build_url(
            '/api/experiments/{experiment_id}/features/{feature_id}'.format(
                experiment_id=self._experiment_id, feature_id=feature_id
            )
        )
        res = self._session.put(url, json=content)
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
        :class:`tmserver.api.mapobject.rename_mapobject_type`
        :class:`tmlib.models.mapobject.MapobjectType`
        '''
        logger.info(
            'rename mapobject type "%s" of experiment "%s"',
            name, self.experiment_name
        )
        content = {'name': new_name}
        mapobject_type_id = self._get_mapobject_type_id(name)
        url = self._build_url(
            '/api/experiments/{experiment_id}/mapobject_types/{mapobject_type_id}'.format(
                experiment_id=self._experiment_id,
                mapobject_type_id=mapobject_type_id
            )
        )
        res = self._session.put(url, json=content)
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
        url = self._build_url(
            '/api/experiments/{experiment_id}/mapobject_types'.format(
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
        :func:`tmserver.api.mapobject.get_features`
        :class:`tmlib.models.feature.Feature`
        '''
        logger.info(
            'get features of experiment "%s", object type "%s"',
            self.experiment_name, mapobject_type_name
        )
        mapobject_type_id = self._get_mapobject_type_id(mapobject_type_name)
        url = self._build_url(
            '/api/experiments/{experiment_id}/mapobject_types/{mapobject_type_id}/features'.format(
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

    def _download_object_feature_values(self, mapobject_type_name, plate_name,
            well_name, well_pos_y, well_pos_x, tpoint):
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
        url = self._build_url(
            '/api/experiments/{experiment_id}/mapobject_types/{mapobject_type_id}/feature-values'.format(
                experiment_id=self._experiment_id,
                mapobject_type_id=mapobject_type_id
            ),
            params
        )
        res = self._session.get(url)
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
        :func:`tmserver.api.mapobject.upload_mapobject_feature_values`
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
        url = self._build_url(
            '/api/experiments/{experiment_id}/mapobject_types/{mapobject_type_id}/feature-values'.format(
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
        :func:`tmserver.api.mapobject.get_mapobject_feature_values`
        :class:`tmlib.models.feature.FeatureValues`
        '''
        res = self._download_feature_values(
            mapobject_type_name, plate_name, well_name, well_pos_y, well_pos_x,
            tpoint
        )
        logger.debug('decode CSV data')
        file_obj = StringIO(res.content)
        return pd.read_csv(file_obj)

    def download_feature_values_and_metadata_files(self, mapobject_type_name,
            plate_name=None, well_name=None, well_pos_y=None, well_pos_x=None,
            tpoint=None, directory=None):
        '''Downloads all feature values for the given object type and writes
        it into a *CSV* file on disk.

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
        directory: str, optional
            absolute path to the directory on disk where the file should be
            saved (defaults to temporary directory)

        See also
        --------
        :meth:`tmclient.api.TmClient.download_object_feature_values`
        :meth:`tmclient.api.TmClient.download_object_metadata`
        '''
        res = self._download_object_feature_values(
            mapobject_type_name, plate_name, well_name, well_pos_y, well_pos_x,
            tpoint
        )
        filename = self._extract_filename_from_headers(res.headers)
        data = res.content
        self._write_file(directory, filename, data)

        res = self._download_object_metadata(
            mapobject_type_name, plate_name, well_name, well_pos_y, well_pos_x,
            tpoint
        )
        filename = self._extract_filename_from_headers(res.headers)
        data = res.content
        self._write_file(directory, filename, data)

    def _download_object_metadata(self, mapobject_type_name, plate_name, well_name,
            well_pos_y, well_pos_x, tpoint):
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
        url = self._build_url(
            '/api/experiments/{experiment_id}/mapobject_types/{mapobject_type_id}/metadata'.format(
                experiment_id=self._experiment_id,
                mapobject_type_id=mapobject_type_id
            ),
            params
        )
        res = self._session.get(url)
        res.raise_for_status()
        return res

    def download_object_metadata(self, mapobject_type_name, plate_name=None,
            well_name=None, well_pos_y=None, well_pos_x=None, tpoint=None,
            directory=None):
        '''Downloads all metadata for the given object type.

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
        :func:`tmserver.api.mapobject.get_mapobject_metadata`
        :class:`tmlib.models.mapobject.MapobjectType`
        '''
        res = self._download_object_metadata(
            mapobject_type_name, plate_name, well_name, well_pos_y, well_pos_x,
            tpoint
        )
        file_obj = StringIO(res.content)
        return pd.read_csv(file_obj)
