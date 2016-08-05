import requests
import json
import logging

from tmlib.models.status import FileUploadStatus
from tmlib.utils import same_docstring_as

from tmclient.experiment import ExperimentQueryService


logger = logging.getLogger(__name__)


class UploadService(ExperimentQueryService):

    '''Class for uploading image and metadata files to TissueMAPS via its
    RESTful API.
    '''

    @same_docstring_as(ExperimentQueryService.__init__)
    def __init__(self, hostname):
        super(UploadService, self).__init__(hostname)

    def get_uploaded_filenames(self, acquisition_id):
        '''Gets the names of files that have already been successfully
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
            if f['status'] == FileUploadStatus.COMPLETE
        ]

    def _get_image_files(self, acquisition_id):
        logger.debug(
            'get image files for acquisition %s', acquisition_id
        )
        url = self.build_url(
            '/api/acquisitions/' + acquisition_id + '/image_files'
        )
        res = self.session.get(url)
        self._handle_error(res)
        return res.json()['data']

    def _get_metadata_files(self, acquisition_id):
        logger.debug(
            'get metadata files for acquisition %s', acquisition_id
        )
        url = self.build_url(
            '/api/acquisitions/' + acquisition_id + '/metadata_files'
        )
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
        url = self.build_url(
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
            ID of the acquisition to which the file belongs
        filepath: str
            absolute path to the file that should be uploaded
        '''
        logger.debug(
            'upload file "%s" for acquisition %s', filepath, acquisition_id
        )
        url = self.build_url(
            '/api/acquisitions/' + acquisition_id + '/upload/upload-file'
        )
        files = {'file': open(filepath, 'rb')}
        res = self.session.post(url, files=files)
        self._handle_error(res)
