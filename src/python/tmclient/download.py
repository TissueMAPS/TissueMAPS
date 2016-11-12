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
import requests
import os
import cgi
import re
import json
import cv2
import pandas as pd
from cStringIO import StringIO
import logging
import tempfile

from tmclient.experiment import ExperimentService


logger = logging.getLogger(__name__)


class DownloadService(ExperimentService):

    '''Class for downloading image files from TissueMAPS via its RESTful API.'''

    def __init__(self, host, port, experiment_name, user_name, password):
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
        super(DownloadService, self).__init__(
            host, port, experiment_name, user_name, password
        )

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
        response = self.session.get(url)
        self._handle_error(response)
        return response

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
        return cv2.imdecode(response.content)

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
        self._handle_error(response)
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
        Tuple[numpy.ndarray[numpy.int32], str]
            labeled image where each label encodes a segmented object and
            filename

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
        return response.content

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
