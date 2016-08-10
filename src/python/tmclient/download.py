import requests
import os
import re
import json
import logging
import tempfile

from tmlib.models.status import FileUploadStatus
from tmlib.utils import same_docstring_as

from tmclient.experiment import ExperimentService


logger = logging.getLogger(__name__)


class DownloadService(ExperimentService):

    '''Class for downloading image files from TissueMAPS via its RESTful API.'''

    @same_docstring_as(ExperimentService.__init__)
    def __init__(self, hostname):
        super(DownloadService, self).__init__(hostname)

    @classmethod
    def _extract_filename_from_headers(cls, headers):
        attachement = headers['content-disposition']
        match = re.search('filename=(.+)', attachement)
        if not match:
            raise ValueError('Filename could not be extracted from header.')
        return match.group(1)

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
        with open(filepath, 'w') as f:
            f.write(data)

    def _download_channel_image(self, experiment_id, channel_name,
            plate_name, well_name, well_pos_y, well_pos_x,
            cycle_index=0, tpoint=0, zplane=0, correct=True):
        logger.info(
            'download image of channel "%s" for experiment %s',
            channel_name, experiment_id
        )
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
                experiment_id, channel_name
            ),
            params
        )
        response = self.session.get(url)
        self._handle_error(response)
        return response

    def download_channel_image(self, experiment_id, channel_name,
            plate_name, well_name, well_pos_y, well_pos_x,
            cycle_index=0, tpoint=0, zplane=0, correct=True):
        '''Downloads a channel image.

        Parameters
        ----------
        experiment_id: str
            ID of the parent experiment
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
        :py:class:`tmlib.models.ChannelImageFile`
        '''
        response = self._download_channel_image(
            experiment_id, channel_name,
            plate_name, well_name, well_pos_y, well_pos_x,
            cycle_index=0, tpoint=0, zplane=0, correct=True
        )
        return response.content

    def download_channel_image_file(self, experiment_id, channel_name,
            plate_name, well_name, well_pos_y, well_pos_x,
            cycle_index=0, tpoint=0, zplane=0, correct=True, directory=None):
        '''Downloads a channel image and writes it to a `PNG` file on disk.

        Parameters
        ----------
        experiment_id: str
            ID of the parent experiment
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
        `tmclient.dowload.Downloadservice.download_channel_image`
        '''
        response = self._download_channel_image(
            experiment_id, channel_name,
            plate_name, well_name, well_pos_y, well_pos_x,
            cycle_index=0, tpoint=0, zplane=0, correct=True
        )
        data = response.content
        filename = self._extract_filename_from_headers(response.headers)
        self._write_file(directory, filename, data)

    def _download_segmentation_image(self, experiment_id, object_name,
            plate_name, well_name, well_pos_y, well_pos_x, tpoint=0, zplane=0):
        logger.info(
            'download segmentated objects "%s" for experiment %s',
            object_name, experiment_id
        )
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
                experiment_id, object_name
            ),
            params
        )
        response = self.session.get(url)
        self._handle_error(response)
        return response

    def download_segmentation_image(self, experiment_id, object_name,
            plate_name, well_name, well_pos_y, well_pos_x, tpoint=0, zplane=0):
        '''Downloads a segmentation image.

        Parameters
        ----------
        plate_id: int
            ID of the parent experiment
        object_name: str
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
        `tmlib.models.Mapobject`
        `tmlib.models.MapobjectType`
        `tmlib.models.MapobjectSegmentation`
        '''
        response = self._download_segmentation_image(
            experiment_id, object_name,
            plate_name, well_name, well_pos_y, well_pos_x, tpoint=0, zplane=0
        )
        return response.content

    def download_segmentation_image_file(self, experiment_id, object_name,
            plate_name, well_name, well_pos_y, well_pos_x, tpoint=0, zplane=0,
            directory=None):
        '''Downloads a segmentation image and writes it to a `PNG` file on disk.

        Parameters
        ----------
        plate_id: int
            ID of the parent experiment
        object_name: str
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
        '''
        response = self._download_segmentation_image(
            experiment_id, object_name,
            plate_name, well_name, well_pos_y, well_pos_x, tpoint=0, zplane=0
        )
        data = response.content
        filename = self._extract_filename_from_headers(response.headers)
        self._write_file(directory, filename, data)

    def download_features_file(self, experiment_id, object_name, directory=None):
        '''Downloads all feature values for the given object type and writes
        it into a zipped archive on disk.
        The archive will contain two `CSV` files, one for the actual feature
        data in form of a *n*x*p* matrix, where *n* is the number of objects
        and *p* the number of features and an additional one for the
        corresponding metadata in form of *n*x*q* table, where *n* is the number
        of objects and *q* the number of metadata attributes.

        Parameters
        ----------
        experiment_id: int
            ID of the parent experiment
        object_name: str
            name of the segmented objects
        directory: str, optional
            absolute path to the directory on disk where the file should be saved
            (defaults to temporary directory)
        '''
        logger.info(
            'download features of "%s" for experiment %s',
            object_name, experiment_id
        )
        url = self.build_url(
            '/api/experiments/%s/mapobjects/%s/feature-values' % (
                experiment_id, object_name
            )
        )
        res = self.session.get(url)
        self._handle_error(res)
        data = res.content
        filename = self._extract_filename_from_headers(res.headers)
        self._write_file(directory, filename, data)
