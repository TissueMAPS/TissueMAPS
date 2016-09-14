import os
import requests
import json
import logging

from tmclient.experiment import ExperimentService


logger = logging.getLogger(__name__)


class UploadService(ExperimentService):

    '''Class for uploading image and metadata files to TissueMAPS via its
    RESTful API.
    '''

    def __init__(self, host_name, experiment_name, user_name, password):
        '''
        Parameters
        ----------
        host_name: str
            name of the TissueMAPS instance
        experiment_name: str
            name of the experiment that should be queried
        user_name: str
            name of the TissueMAPS user
        password: str
            password for `username`
        '''
        super(UploadService, self).__init__(
            host_name, experiment_name, user_name, password
        )

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
        self._handle_error(res)
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
        self._handle_error(res)
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
        for name in registered_filenames:
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
        self._handle_error(res)
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
        self._handle_error(res)
