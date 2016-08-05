import requests
import os
import re
import json
import logging

from tmlib.models.status import FileUploadStatus
from tmlib.utils import same_docstring_as

from tmclient.experiment import ExperimentQueryService


logger = logging.getLogger(__name__)


class DownloadService(ExperimentQueryService):

    '''Class for downloading image files from TissueMAPS via its RESTful API.
    '''

    @same_docstring_as(ExperimentQueryService.__init__)
    def __init__(self, hostname):
        super(DownloadService, self).__init__(hostname)

    @staticmethod
    def _extract_filename_from_headers(headers):
        attachement = headers['content-disposition']
        match = re.search('filename=(.+)', attachement)
        if not match:
            raise ValueError('Filename could not be extracted from header.')
        return match.group(1)

    def download_channel_image_file(self, cycle_id, folder, channel_name,
            well_name, well_pos_y, well_pos_x, tpoint=0, zplane=0, correct=True):
        '''Downloads a :py:class:`tmlib.models.ChannelImageFile` and writes it
        to a `PNG` file on disk.

        Parameters
        ----------
        cycle_id: str
            ID of the cycle to which the image belongs
        folder: str
            absolute path to the folder on disk where the file should be saved
        channel_name: str
            name of the channel
        well_name: str
            name of the well in which the image is located
        well_pos_x: int
            x-position of the image relative to the well grid
        well_pos_y: int
            y-position of the image relative to the well grid
        tpoint: int, optional
            time point (default: ``0``)
        zplane: int, optional
            z-position of the image (default: ``0``)
        correct: bool, optional
            whether image should be corrected for illumination artifacts
            (default: ``True``)

        Note
        ----
        Image gets automatically aligned between cycles.
        '''
        logger.debug(
            'download channel image file for cycle #%d', cycle_id
        )
        params = {
            'channel_name': channel_name,
            'well_name': well_name,
            'x': well_pos_x,
            'y': well_pos_y,
            'tpoint': tpoint,
            'zplane': zplane,
            'correct': correct
        }
        url = self.build_url(
            '/api/cycles/' + cycle_id + '/image-files', params
        )
        res = self.session.get(url)
        self._handle_error(res)
        data = res.content
        filename = self._extract_filename_from_headers(res.headers)
        filepath = os.path.join(folder, filename)
        with open(filepath, 'w') as f:
            f.write(data)

    def download_segmentation_image_file(self, plate_id, object_name,
            folder, well_name, well_pos_y, well_pos_x, tpoint=0, zplane=0):
        '''Downloads :py:class:`tmlib.models.MapobjectSegmentation` and writes
        it to a `PNG` file on disk.

        Parameters
        ----------
        plate_id: int
            ID of the experiment to which segmented objects belong
        object_name: str
            name of the segmented objects
        folder: str
            absolute path to the folder on disk where the file should be saved
        channel_name: str
            name of the channel
        well_name: str
            name of the well in which the image is located
        well_pos_x: int
            x-position of the image relative to the well grid
        well_pos_y: int
            y-position of the image relative to the well grid
        tpoint: int, optional
            time point (default: ``0``)
        zplane: int, optional
            z-position of the image (default: ``0``)

        Note
        ----
        Image gets automatically aligned between cycles.
        '''
        logger.debug(
            'download segmentation image file for plate #%d and objects "%s"',
            plate_id, object_name
        )
        params = {
            'well_name': well_name,
            'x': well_pos_x,
            'y': well_pos_y,
            'tpoint': tpoint,
            'zplane': zplane
        }
        url = self.build_url(
            '/api/plates/' + plate_id + '/mapobjects/' + object_name +
            '/segmentations', params
        )
        res = self.session.get(url)
        self._handle_error(res)
        data = res.content
        filename = self._extract_filename_from_headers(res.headers)
        filepath = os.path.join(folder, filename)
        with open(filepath, 'w') as f:
            f.write(data)
