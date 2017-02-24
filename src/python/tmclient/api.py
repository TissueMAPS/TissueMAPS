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
        self._experiment_id = self._get_experiment_id(experiment_name)

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
            description='TissueMAPS REST API client.',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        parser.add_argument(
            '-H', '--host', required=True,
            help='name of TissueMAPS server host'
        )
        parser.add_argument(
            '-P', '--port', type=int, default=80,
            help='number of the port to which the TissueMAPS server listens'
        )
        parser.add_argument(
            '-u', '--user_name', required=True,
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
            '-e', '--experiment_name', required=True,
            help='name of the parent experiment'
        )

        subparsers = parser.add_subparsers(
            dest='request_type', help='request type'
        )
        subparsers.required = True

        create_parser = subparsers.add_parser(
            'create', help='create new database entries',
            description='Create new database entries.',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )

        create_subparsers = create_parser.add_subparsers(
            dest='data_model', help='data model'
        )

        experiment_parser = create_subparsers.add_parser(
            'experiment', help='create a new experiment',
            description='Create a new experiment.',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        experiment_parser.set_defaults(method='create_experiment')
        experiment_parser.add_argument(
            '--microscope_type', '-m', default='cellvoyager',
            help='microscope type'
        )
        experiment_parser.add_argument(
            '--plate_format', '-f', type=int, default=384,
            help='''
                well-plate format, i.e. total number of wells per plate
            '''
        )
        experiment_parser.add_argument(
            '--plate_acquisition_mode', default='basic',
            choices={'basic', 'multiplexing'},
            help='''
                whether multiple acquisitions of the same plate are interpreted
                as time points ("basic" mode) or multiplexing cycles
                ("multiplexing" mode)
            '''
        )

        plate_parser = create_subparsers.add_parser(
            'plate', help='create a new plate for an existing experiment',
            description='Create a new plate.',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        plate_parser.set_defaults(method='create_plate')
        plate_parser.add_argument(
            '-p', '--plate_name', required=True,
            help='name of the plate that should be created'
        )

        acquisition_parser = create_subparsers.add_parser(
            'acquisition', help='create a new acquisition for an existing plate',
            description='Create a new acquisition.',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        acquisition_parser.set_defaults(method='create_acquisition')
        acquisition_parser.add_argument(
            '-p', '--plate_name', required=True,
            help='name of the parent plate'
        )
        acquisition_parser.add_argument(
            '-a', '--acquisition_name', required=True,
            help='name of the acquisition that should be created'
        )

        upload_parser = subparsers.add_parser(
            'upload', help='upload data',
            description='Upload data.',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        upload_parser.add_argument(
            '-d', '--directory', required=True,
            help='path to directory where files should be uploaded from'
        )

        upload_subparsers = upload_parser.add_subparsers(
            dest='file_type', help='file type'
        )
        upload_subparsers.required = True

        microscope_file_parser = upload_subparsers.add_parser(
            'microscope_file',
            help='upload microscope image and metadata files',
            description='Upload microscope image and metadata files.',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        microscope_file_parser.set_defaults(method='upload_microscope_files')
        microscope_file_parser.add_argument(
            '-p', '--plate_name', required=True,
            help='name of the plate'
        )
        microscope_file_parser.add_argument(
            '-a', '--acquisition_name', required=True,
            help='name of the acquisition'
        )

        download_parser = subparsers.add_parser(
            'download', help='download data',
            description='Download data.',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        download_parser.add_argument(
            '-d', '--directory',
            help='path to directory where files should be downloaded to'
        )

        download_subparsers = download_parser.add_subparsers(
            dest='file_type', help='file type'
        )
        download_subparsers.required = True

        image_position_parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        image_position_parser.add_argument(
            '-p', '--plate_name', required=True,
            help='name of the plate'
        )
        image_position_parser.add_argument(
            '-w', '--well_name', required=True,
            help='name of the well'
        )
        image_position_parser.add_argument(
            '-x', '--well_pos_x', required=True,
            help='zero-based x cooridinate of acquisition site within the well'
        )
        image_position_parser.add_argument(
            '-y', '--well_pos_y', required=True,
            help='zero-based y cooridinate of acquisition site within the well'
        )
        image_position_parser.add_argument(
            '-z', '--zplane', default=0,
            help='zero-based z-plane index'
        )
        image_position_parser.add_argument(
            '-t', '--tpoint', default=0,
            help='zero-based time point index'
        )

        channel_image_parser = download_subparsers.add_parser(
            'channel_image', help='download channel image',
            parents=[image_position_parser],
            description='Download channel image.',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        channel_image_parser.set_defaults(method='download_channel_image_file')
        channel_image_parser.add_argument(
            '-c', '--channel_name', required=True,
            help='name of the channel'
        )
        channel_image_parser.add_argument(
            '-i', '--cycle_index', default=0,
            help='zero-based index of the cycle'
        )
        channel_image_parser.add_argument(
            '--correct', action='store_true',
            help='whether image should be corrected for illumination artifacts'
        )

        segmentation_image_parser = download_subparsers.add_parser(
            'segmentation_image',
            help='download segmented objects as label image',
            description='Download segmentation image.',
            parents=[image_position_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        segmentation_image_parser.set_defaults(
            method='download_segmentation_image_file'
        )
        segmentation_image_parser.add_argument(
            '-o', '--object_type', required=True,
            help='type of the segmented objects (e.g. Cells)'
        )

        object_parser = argparse.ArgumentParser(
            add_help=False,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        object_parser.add_argument(
            '-o', '--object_type', required=True,
            help='type of the segmented objects (e.g. Cells)'
        )

        feature_value_parser = download_subparsers.add_parser(
            'feature_values', help='download object feature values',
            description='Download feature values for segmented objects.',
            parents=[object_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        feature_value_parser.set_defaults(method='download_object_feature_values_file')

        metadata_parser = download_subparsers.add_parser(
            'metadata', help='download object metadata',
            description='Download metadata for segmented objects.',
            parents=[object_parser],
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        metadata_parser.set_defaults(method='download_object_metadata_file')

        return parser

    def _get_experiment_id(self, experiment_name):
        '''Gets the ID of an existing experiment given its name.

        Parameters
        ----------
        experiment_name: str
            name of the experiment

        Returns
        -------
        str
            experiment ID

        '''
        logger.debug('get ID for experiment "%s"', experiment_name)
        params = {
            'name': experiment_name,
        }
        url = self.build_url('/api/experiments', params)
        res = self.session.get(url)
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
        :class:`tmlib.models.experiment.ExperimentReference`
        :class:`tmlib.models.experiment.Experiment`
        '''
        logger.info('create experiment "%s"', experiment_name)
        data = {
            'name': self.experiment_name,
            'microscope_type': microscope_type,
            'plate_format': plate_format,
            'plate_acquisition_mode': plate_acquisition_mode
        }
        url = self.build_url('/api/experiments')
        res = self.session.post(url, json=data)
        res.raise_for_status()

    def _get_plate_id(self, plate_name):
        '''Gets the ID of an existing plate given its name.

        Parameters
        ----------
        plate_name: str
            name of the plate

        Returns
        -------
        str
            plate ID

        '''
        logger.debug('get ID for plate "%s"' % plate_name)
        params = {
            'name': plate_name,
        }
        url = self.build_url(
            '/api/experiments/%s/plates' % self._experiment_id, params
        )
        res = self.session.get(url)
        res.raise_for_status()
        data = res.json()['data']
        if len(data) > 1:
            raise QueryError(
                'More than one plate found with name "%s"' % name
            )
        elif len(data) == 0:
            raise QueryError(
                'No plate found with name "%s"' % name
            )
        return data[0]['id']

    def create_plate(self, plate_name):
        '''Creates a new plate.

        Parameters
        ----------
        plate_name: str
            name that should be given to the plate

        See also
        --------
        :class:`tmlib.models.plate.Plate`
        '''
        logger.info('create plate "%s"', plate_name)
        data = {
            'name': plate_name,
        }
        url = self.build_url('/api/experiments/%s/plates' % self._experiment_id)
        res = self.session.post(url, json=data)
        res.raise_for_status()

    def _get_acquisition_id(self, plate_name, acquisition_name):
        '''Gets the ID of an existing acquisition given its name and the name
        of the parent plate.

        Parameters
        ----------
        plate_name: str
            name of the parent plate
        acquisition_name: str
            name of the acquisition

        Returns
        -------
        str
            acquisition ID

        '''
        logger.debug(
            'get acquisition ID given acquisition "%s" and plate "%s"',
            acquisition_name, plate_name
        )
        params = {
            'plate_name': plate_name,
            'name': acquisition_name
        }
        url = self.build_url(
            '/api/experiments/%s/acquisitions' % self._experiment_id,
            params
        )
        res = self.session.get(url)
        res.raise_for_status()
        data = res.json()['data']
        if len(data) > 1:
            raise QueryError(
                'More than one acquisition found with name "%s" and '
                'plate name "%s".' % (acquisition_name, plate_name)
            )
        elif len(data) == 0:
            raise QueryError(
                'No acquisition found with name "%s" and '
                'plate name "%s".' % (acquisition_name, plate_name)
            )
        return data[0]['id']

    def create_acquisition(self, plate_name, acquisition_name):
        '''Creates a new acquisition.

        Parameters
        ----------
        plate_name: str
            name of the parent plate
        acquisition_name: str
            name that should be given to the acquisition

        See also
        --------
        :class:`tmlib.models.acquisition.Acquisition`
        '''
        logger.info(
            'create acquisition "%s" for plate "%s"',
            acquisition_name, plate_name
        )
        data = {
            'plate_name': plate_name,
            'name': acquisition_name
        }
        url = self.build_url(
            '/api/experiments/%s/acquisitions' % self._experiment_id
        )
        res = self.session.post(url, json=data)
        res.raise_for_status()

    def _get_cycle_id(self, plate_name, cycle_index):
        '''Gets the ID of a cycle given its index, the name of the parent plate
        and ID of the parent experiment.

        Parameters
        ----------
        plate_name: str
            name of the parent plate
        cycle_index: str
            index of the cycle

        Returns
        -------
        str
            cycle ID

        '''
        logger.debug(
            'get cycle ID given cycle #%d and plate "%s"',
            cycle_index, plate_name
        )
        params = {
            'plate_name': plate_name,
            'index': cycle_index
        }
        url = self.build_url(
            '/api/experiments/%s/cycles/id' % self._experiment_id, params
        )
        res = self.session.get(url)
        res.raise_for_status()
        data = res.json()['data']
        if len(data) > 1:
            raise QueryError(
                'More than one cycle found with index %d and '
                'plate name "%s".' % (cycle_index, plate_name)
            )
        elif len(data) == 0:
            raise QueryError(
                'No cycle found with index %d and '
                'plate name "%s".' % (cycle_index, plate_name)
            )
        return data[0]['id']

    def _get_channel_id(self, channel_name):
        '''Gets the ID of a channel given its name.

        Parameters
        ----------
        channel_name: str
            name of the channel

        Returns
        -------
        str
            channel ID

        '''
        logger.debug('get channel ID given channel "%s"', channel_name)
        params = {
            'name': channel_name,
        }
        url = self.build_url(
            '/api/experiments/%s/channels' % self._experiment_id, params
        )
        res = self.session.get(url)
        res.raise_for_status()
        data = res.json()['data']
        if len(data) > 1:
            raise QueryError(
                'More than one channel found with name "%s".' % channel_name
            )
        elif len(data) == 0:
            raise QueryError(
                'No channel found with name "%s".' % channel_name
            )
        return data[0]['id']

    def _get_channel_layer_id(self, channel_name, tpoint=0, zplane=0):
        '''Gets the ID of a channel layer given the name of the parent channel
        as well as time point and z-plane indices.

        Parameters
        ----------
        channel_name: str
            name of the channel
        tpoint: int, optional
            zero-based time point index (default: ``0``)
        zplane: int, optional
            zero-based z-plane index (default: ``0``)

        Returns
        -------
        str
            channel layer ID

        '''
        logger.debug(
            'get channel ID given channel "%s", tpoint %d and zplane %d',
            channel_name, tpoint, zplane
        )
        params = {
            'channel_name': channel_name,
            'tpoint': tpoint,
            'zplane': zplane
        }
        url = self.build_url(
            '/api/experiments/%s/channel_layers' % self._experiment_id,
            params
        )
        res = self.session.get(url)
        res.raise_for_status()
        data = res.json()['data']
        if len(data) > 1:
            raise QueryError(
                'More than one channel layer found with channel name "%s" '
                'tpoint %d and zplane %d.' % (channel_name, tpoint, zplane)
            )
        elif len(data) == 0:
            raise QueryError(
                'No channel layer found with channel name "%s" '
                'tpoint %d and zplane %d.' % (channel_name, tpoint, zplane)
            )
        return data[0]['id']

    def get_uploaded_filenames(self, plate_name, acquisition_name):
        '''Gets the names of files that have already been successfully
        uploaded.

        Parameters
        ----------
        plate_name: str
            name of the parent plate
        acquisition_name: str
            name of the parent acquisition

        Returns
        -------
        List[str]
            names of uploaded files

        See also
        --------
        :func:`tmserver.api.experiment.get_microscope_image_files`
        :func:`tmserver.api.experiment.get_microscope_metadata_files`
        :class:`tmlib.models.file.MicroscopeImageFile`
        :class:`tmlib.models.file.MicroscopeMetadataFile`
        '''
        acquisition_id = self._get_acquisition_id(plate_name, acquisition_name)
        image_files = self._get_image_files(
            self._experiment_id, acquisition_id
        )
        metadata_files = self._get_metadata_files(
            self._experiment_id, acquisition_id
        )
        return [
            f['name'] for f in image_files + metadata_files
            if f['status'] == 'COMPLETE'
        ]

    def _get_image_files(self, acquisition_id):
        logger.debug(
            'get image files for acquisition %s', acquisition_id
        )
        url = self.build_url(
            '/api/experiments/%s/acquisitions/%s/image-files' % (
                self._experiment_id, acquisition_id
            )
        )
        res = self.session.get(url)
        res.raise_for_status()
        return res.json()['data']

    def _get_metadata_files(self, acquisition_id):
        logger.debug(
            'get metadata files for acquisition %s', acquisition_id
        )
        url = self.build_url(
            '/api/experiments/%s/acquisitions/%s/metadata-files' % (
                self._experiment_id, acquisition_id
            )
        )
        res = self.session.get(url)
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
        :mod:`tmserver.api.upload`
        :class:`tmlib.models.file.MicroscopeImageFile`
        :class:`tmlib.models.file.MicroscopeMetadataFile`
        '''
        # TODO: consider using os.walk() to screen subdirectories recursively
        logger.info(
            'upload microscope files of plate "%s" and acquisition "%s"',
            plate_name, acquisition_name
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
        logger.info(
            'register files for upload of acquisition %s', acquisition_id
        )
        url = self.build_url(
            '/api/experiments/%s/acquisitions/%s/upload/register' % (
                self._experiment_id, acquisition_id
            )
        )
        payload = {'files': filenames}
        res = self.session.post(url, json=payload)
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
            'upload file "%s" for acquisition %s', filepath, acquisition_id
        )
        url = self.build_url(
            '/api/experiments/%s/acquisitions/%s/upload/upload-file' % (
                self._experiment_id, acquisition_id
            )
        )
        files = {'file': open(filepath, 'rb')}
        res = self.session.post(url, files=files)
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
        logger.info('download image of channel "%s"', channel_name)
        params = {
            'plate_name': plate_name,
            'cycle_index': cycle_index,
            'well_name': well_name,
            'x': well_pos_x,
            'y': well_pos_y,
            'tpoint': tpoint,
            'zplane': zplane,
            'correct': correct
        }
        url = self.build_url(
            '/api/experiments/%s/channels/%s/image-files' % (
                self._experiment_id, channel_name
            ),
            params
        )
        res = self.session.get(url)
        res.raise_for_status()
        return res

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
        :meth:`tmclient.download.DownloadService.download_channel_image`
        '''
        response = self._download_channel_image(
            channel_name, plate_name, well_name, well_pos_y, well_pos_x,
            cycle_index=cycle_index, tpoint=tpoint, zplane=zplane,
            correct=correct
        )
        data = response.content
        filename = self._extract_filename_from_headers(response.headers)
        self._write_file(directory, filename, data)

    def _download_segmentation_image(self, object_type, plate_name,
            well_name, well_pos_y, well_pos_x, tpoint=0, zplane=0):
        logger.info('download segmentated objects "%s"', object_type)
        params = {
            'plate_name': plate_name,
            'well_name': well_name,
            'x': well_pos_x,
            'y': well_pos_y,
            'tpoint': tpoint,
            'zplane': zplane
        }
        url = self.build_url(
            '/api/experiments/%s/mapobjects/%s/segmentations' % (
                self._experiment_id, object_type
            ),
            params
        )
        response = self.session.get(url)
        response.raise_for_status()
        return response

    def download_segmentation_image(self, object_type,
            plate_name, well_name, well_pos_y, well_pos_x, tpoint=0, zplane=0):
        '''Downloads a segmentation image.

        Parameters
        ----------
        plate_id: int
            ID of the parent experiment
        object_type: str
            name of the segmented objects
        plate_name: str
            name of the plate
        well_name: str
            name of the well in which the image is located
        well_pos_x: int
            x-position of the image relative to the well grid
        well_pos_y: int
            y-position of the image relative to the well grid
        tpoint: int, optional
            zero-based time point index (default: ``0``)
        zplane: int, optional
            zero-based z-plane index (default: ``0``)

        Note
        ----
        Image gets automatically aligned between cycles.

        Returns
        -------
        numpy.ndarray[numpy.int32]
            labeled image where each label encodes a segmented object

        See also
        --------
        :func:`tmserver.api.experiment.get_segmentation_image`
        :class:`tmlib.models.mapobject.MapobjectSegmentation`
        :class:`tmlib.image.SegmentationImage`
        '''
        response = self._download_segmentation_image(
            object_type, plate_name, well_name, well_pos_y, well_pos_x,
            tpoint=0, zplane=0
        )
        data = np.frombuffer(response.content, np.uint8)
        return cv2.imdecode(data, cv2.IMREAD_UNCHANGED)

    def download_segmentation_image_file(self, object_type,
            plate_name, well_name, well_pos_y, well_pos_x, tpoint=0, zplane=0,
            directory=None):
        '''Downloads a segmentation image and writes it to a `PNG` file on disk.

        Parameters
        ----------
        object_type: str
            name of the segmented objects
        plate_name: str
            name of the plate
        well_name: str
            name of the well in which the image is located
        well_pos_x: int
            x-position of the image relative to the well grid
        well_pos_y: int
            y-position of the image relative to the well grid
        tpoint: int, optional
            zero-based time point index (default: ``0``)
        zplane: int, optional
            zero-based z-plane index (default: ``0``)
        directory: str, optional
            absolute path to the directory on disk where the file should be saved
            (defaults to temporary directory)

        Note
        ----
        Image gets automatically aligned between cycles.

        See also
        --------
        :meth:`tmclient.download.DownloadService.download_segmentation_image`
        '''
        response = self._download_segmentation_image(
            object_type, plate_name, well_name, well_pos_y, well_pos_x,
            tpoint=0, zplane=0
        )
        data = response.content
        filename = self._extract_filename_from_headers(response.headers)
        self._write_file(directory, filename, data)

    def _download_object_feature_values(self, object_type):
        logger.info('download features of "%s"', object_type)
        url = self.build_url(
            '/api/experiments/%s/mapobjects/%s/feature-values' % (
                self._experiment_id, object_type
            )
        )
        res = self.session.get(url)
        res.raise_for_status()
        return res

    def download_object_feature_values(self, object_type):
        '''Downloads all feature values for the given object type.

        Parameters
        ----------
        object_type: str
            type of the segmented objects

        Returns
        -------
        pandas.DataFrame
            *n*x*p* dataframe, where *n* are number of objects and *p* number
            of features

        See also
        --------
        :func:`tmserver.api.mapobject.get_mapobject_feature_values`
        :class:`tmlib.models.mapobject.MapobjectType`
        :class:`tmlib.models.mapobject.Mapobject`
        :class:`tmlib.models.feature.Feature`
        :class:`tmlib.models.feature.FeatureValue`
        '''
        res = self._download_object_feature_values(object_type)
        file_obj = StringIO(res.content)
        return pd.read_csv(file_obj)

    def download_object_feature_values_file(self, object_type, directory=None):
        '''Downloads all feature values for the given object type and writes
        it into a *CSV* file on disk.

        Parameters
        ----------
        object_type: str
            type of the segmented objects
        directory: str, optional
            absolute path to the directory on disk where the file should be
            saved (defaults to temporary directory)

        See also
        --------
        :meth:`tmclient.download.DownloadService.download_object_feature_values`
        '''
        res = self._download_object_feature_values(object_type)
        filename = self._extract_filename_from_headers(res.headers)
        data = res.content
        self._write_file(directory, filename, data)

    def _download_object_metadata(self, object_type):
        logger.info('download metadata of "%s"', object_type)
        url = self.build_url(
            '/api/experiments/%s/mapobjects/%s/metadata' % (
                self._experiment_id, object_type
            )
        )
        res = self.session.get(url)
        res.raise_for_status()
        return res

    def download_object_metadata(self, object_type):
        '''Downloads all metadata for the given object type.

        Parameters
        ----------
        object_type: str
            type of the segmented objects

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
        res = self._download_object_metadata(object_type)
        return pd.read_csv(res.content)

    def download_object_metadata_file(self, object_type, directory=None):
        '''Downloads all metadata for the given object type and writes
        it into a *CSV* file on disk.

        Parameters
        ----------
        object_type: str
            type of the segmented objects
        directory: str, optional
            absolute path to the directory on disk where the file should be
            saved (defaults to temporary directory)

        See also
        --------
        :meth:`tmclient.download.DownloadService.download_object_metadata`
        '''
        res = self._download_object_metadata(object_type)
        filename = self._extract_filename_from_headers(res.headers)
        data = res.content
        self._write_file(directory, filename, data)
