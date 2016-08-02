import requests
import json
import logging

from tmlib.models.status import FileUploadStatus
from tmlib.utils import same_docstring_as

from tmclient.base import HttpClient


logger = logging.getLogger(__name__)


class FileUploader(HttpClient):

    '''Class for uploading image and metadata files to TissueMAPS via
    RESTful API.
    '''

    @same_docstring_as(HttpClient.__init__)
    def __init__(self, hostname):
        super(FileUploader, self).__init__(hostname)

    def get_uploaded_files(self, acquisition_id):
        '''Gets a list of files that have already been successfully
        uploaded.

        Parameters
        ----------
        acquisition_id: str
            encoded acquisition ID

        Returns
        -------
        List[str]
            names of uploaded files
        '''
        image_files = self._get_image_files(acquisition_id)
        metadata_files = self._get_metadata_files(acquisition_id)
        return [
            f['name'] for f in image_files + metadata_files
            if f['upload_status'] == FileUploadStatus.COMPLETE
        ]

    def _get_image_files(self, acquisition_id):
        logger.debug(
            'get image files for acquisition %s', acquisition_id
        )
        url = self.get_url(
            '/api/acquisitions/' + acquisition_id + '/image_files'
        )
        res = self.session.get(url)
        self._handle_error(res)
        return res.json()['data']

    def _get_metadata_files(self, acquisition_id):
        logger.debug(
            'get metadata files for acquisition %s', acquisition_id
        )
        url = self.get_url(
            '/api/acquisitions/' + acquisition_id + '/metadata_files'
        )
        res = self.session.get(url)
        self._handle_error(res)
        return res.json()['data']

    def get_acquisition_id(self, experiment_name, plate_name, acquisition_name):
        '''Gets the encoded acquisition ID for a given experiment,
        plate and acquisition.

        Parameters
        ----------
        experiment_name: str
            name of the parent experiment
        plate_name: str
            name of the parent plate
        acquisition_name: str
            name of the acquisition

        Returns
        -------
        str
            encoded acquisition ID
        '''
        logger.debug(
            'get acquisition ID for experiment "%s", plate "%s" and '
            'acquisition "%s"', experiment_name, plate_name, acquisition_name
        )
        params = {
            'experiment_name': experiment_name,
            'plate_name': plate_name,
            'acquisition_name': acquisition_name
        }
        url = self.get_url('/api/acquisitions/id', params)
        res = self.session.get(url)
        self._handle_error(res)
        return res.json()['data']

    def register_files_for_upload(self, acquisition_id, filenames):
        '''Registers files for upload.

        Parameters
        ----------
        acquisition_id: str
            encoded acquisition ID
        filenames: List[str]
            names of files that should be uploaded

        Returns
        -------
        List[str]
            names of valid files that have been registered
        '''
        logger.debug(
            'register files for upload for acquisition %s', acquisition_id
        )
        url = self.get_url(
            '/api/acquisitions/' + acquisition_id + '/upload/register'
        )
        payload = {'files': filenames}
        res = self.session.put(url, json=payload)
        self._handle_error(res)
        return res.json()['data']

    def upload_file(self, acquisition_id, filepath):
        '''Uploads an individual file.

        Parameters
        ----------
        acquisition_id: str
            encoded acquisition ID
        filepath: str
            absolute path to the file that should be uploaded
        '''
        logger.debug(
            'upload file "%s" for acquisition %s', filepath, acquisition_id
        )
        url = self.get_url(
            '/api/acquisitions/' + acquisition_id + '/upload/upload-file'
        )
        files = {'file': open(filepath, 'rb')}
        res = self.session.post(url, files=files)
        self._handle_error(res)
