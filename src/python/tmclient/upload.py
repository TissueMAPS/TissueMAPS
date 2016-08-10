import requests
import json
import logging

from tmlib.models.status import FileUploadStatus
from tmlib.utils import same_docstring_as

from tmclient.experiment import ExperimentService


logger = logging.getLogger(__name__)


class UploadService(ExperimentService):

    '''Class for uploading image and metadata files to TissueMAPS via its
    RESTful API.
    '''

    @same_docstring_as(ExperimentService.__init__)
    def __init__(self, hostname):
        super(UploadService, self).__init__(hostname)

    def get_uploaded_filenames(self, experiment_id, acquisition_id):
        '''Gets the names of files that have already been successfully
        uploaded.

        Parameters
        ----------
        experiment_id: str
            ID of the parent experiment
        acquisition_id: str
            ID of the acquisition

        Returns
        -------
        List[str]
            names of uploaded files
        '''
        image_files = self._get_image_files(experiment_id, acquisition_id)
        metadata_files = self._get_metadata_files(experiment_id, acquisition_id)
        return [
            f['name'] for f in image_files + metadata_files
            if f['status'] == FileUploadStatus.COMPLETE
        ]

    def _get_image_files(self, acquisition_id):
        logger.debug(
            'get image files for acquisition %s', acquisition_id
        )
        url = self.build_url(
            '/api/experiments/%s/acquisitions/%s/image-files' % (
                experiment_id, acquisition_id
            )
        )
        res = self.session.get(url)
        self._handle_error(res)
        return res.json()['data']

    def _get_metadata_files(self, experiment_id, acquisition_id):
        logger.debug(
            'get metadata files for acquisition %s', acquisition_id
        )
        url = self.build_url(
            '/api/experiments/%s/acquisitions/%s/metadata-files' % (
                experiment_id, acquisition_id
            )
        )
        res = self.session.get(url)
        self._handle_error(res)
        return res.json()['data']

    def register_files_for_upload(self, experiment_id, acquisition_id, filenames):
        '''Registers microscope files for upload.

        Parameters
        ----------
        experiment_id: str
            ID of the parent experiment
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
            'register files for upload for acquisition %s', acquisition_id
        )
        url = self.build_url(
            '/api/experiments/%s/acquisitions/%s/upload/register' % (
                experiment_id, acquisition_id
            )
        )
        payload = {'files': filenames}
        res = self.session.put(url, json=payload)
        self._handle_error(res)
        return res.json()['data']

    def upload_microscope_files(self, experiment_id, plate_name,
            acquisition_name, directory):
        '''Registers and uploads microscope files contained in `directory`.

        Parameters
        ----------
        experiment_id: int
            ID of the parent experiment

        '''
        # TODO: consider using os.walk() to screen subdirectories recursively
        logger.info(
            'upload microscope files of plate "%s" and acquisition "%s"'
            'for experiment "%s"', plate_name, acquisition_name, experiment_id
        )
        directory = os.path.expanduser(directory)
        directory = os.path.expandvars(directory)
        filenames = os.listdir(directory)
        acquisition_id = self.get_acquisition_id(
            experiment_id, args.plate_name, args.acquisition_name
        )
        registered_filenames = self.register_files_for_upload(
            experiment_id, acquisition_id, filenames
        )
        for name in registered_filenames:
            logger.info('upload file: %s', name)
            filepath = os.path.join(directory, name)
            self.upload_file(experiment_id, acquisition_id, filepath)

    def upload_file(self, experiment_id, acquisition_id, filepath):
        '''Uploads an individual file.

        Parameters
        ----------
        experiment_id: str
            ID of the parent experiment
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
                experiment_id, acquisition_id
            )
        )
        files = {'file': open(filepath, 'rb')}
        res = self.session.post(url, files=files)
        self._handle_error(res)
