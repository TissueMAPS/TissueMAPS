"""API view functions for file upload during the setup process"""
import os.path as p
import json
import datetime
import importlib
import logging
import re

from flask import request
from flask_jwt import jwt_required
from werkzeug import secure_filename
from sqlalchemy.orm.exc import MultipleResultsFound

import tmlib.models as tm
from tmlib.models.status import FileUploadStatus
from tmlib.workflow.metaconfig import get_microscope_type_regex

from tmserver.extensions import redis_store
from tmserver.api import api
from tmserver.util import decode_query_ids, decode_form_ids
from tmserver.util import assert_query_params, assert_form_params
from tmserver.error import *

logger = logging.getLogger(__name__)


@api.route(
    '/experiments/<experiment_id>/acquisitions/<acquisition_id>/upload/register',
    methods=['POST']
)
@jwt_required()
@assert_form_params('files')
@jwt_required()
@decode_query_ids()
def register_upload(experiment_id, acquisition_id):
    """
    .. http:post:: /api/experiments/(string:experiment_id)/acquisitions/(string:acquisition_id)/upload/register

        Notify the server that an upload for this acquisition is imminent.
        The client has to wait for this response before uploading files.

        **Example request**:

        .. sourcecode:: http

            Content-Type: application/json

            {
                files: ["file1.png", "file2.png", ...]
            }

        **Example response**:

        .. sourcecode:: http

            Content-Type: application/json

            {
                "data": ["file1.png", "file2.png", ...]
            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 500: server error

    """
    data = request.get_json()
    files = data['files']

    if len(files) == 0:
        raise MalformedRequestError(
            'No files supplied. Cannot register upload.'
        )

    with tm.utils.ExperimentSession(experiment_id) as session:
        experiment = session.query(tm.Experiment).one()
        microscope_type = experiment.microscope_type
        img_regex, metadata_regex = get_microscope_type_regex(microscope_type)
        acquisition = session.query(tm.Acquisition).get(acquisition_id)
        img_filenames = [f.name for f in acquisition.microscope_image_files]
        img_files = [
            tm.MicroscopeImageFile(
                name=secure_filename(f), acquisition_id=acquisition.id
            )
            for f in files
            if img_regex.search(f) and
            secure_filename(f) not in img_filenames
        ]
        meta_filenames = [f.name for f in acquisition.microscope_metadata_files]
        meta_files = [
            tm.MicroscopeMetadataFile(
                name=secure_filename(f), acquisition_id=acquisition.id
            )
            for f in files
            if metadata_regex.search(f) and
            secure_filename(f) not in meta_filenames
        ]

        session.bulk_save_objects(img_files + meta_files)

        # Trigger creation of directories
        acquisition.location
        acquisition.microscope_images_location
        acquisition.microscope_metadata_location

    with tm.utils.ExperimentSession(experiment_id) as session:
        image_file_names = session.query(tm.MicroscopeImageFile.name).\
            filter(tm.MicroscopeImageFile.status != FileUploadStatus.COMPLETE).\
            all()
        metadata_file_names = session.query(tm.MicroscopeMetadataFile.name).\
            filter(tm.MicroscopeMetadataFile.status != FileUploadStatus.COMPLETE).\
            all()
        return jsonify({
            'data': [f.name for f in image_file_names + metadata_file_names]
        })


@api.route(
    '/experiments/<experiment_id>/acquisitions/<acquisition_id>/upload/validity-check',
    methods=['POST']
)
@jwt_required()
@assert_form_params('files')
@decode_query_ids()
def file_validity_check(experiment_id, acquisition_id):
    """
    .. http:post:: /api/experiments/(string:experiment_id)/acquisitions/(string:acquisition_id)/upload/validity-check

        Check if a collection of image or metadata file names have the correct format
        for the experiment's microscope type. If this is not the case, the files can't be analyzed
        and shouldn't be uploaded.

        **Example request**:

        .. sourcecode:: http

            Content-Type: application/json

            {
                files: ["right_format_1.png", "right_format_2.png", "wrong_format.png"...]
            }

        **Example response**:

        .. sourcecode:: http

            Content-Type: application/json

            {
                "is_valid": [true, true, false, ...]
            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 500: server error

    """
    data = json.loads(request.data)
    if not 'files' in data:
        raise MalformedRequestError()
    if not type(data['files']) is list:
        raise MalformedRequestError('No image files provided.')

    def check_file(fname):
        is_imgfile = imgfile_regex.search(fname) is not None
        is_metadata_file = metadata_regex.search(fname) is not None
        return is_metadata_file or is_imgfile

    with tm.utils.ExperimentSession(experiment_id) as session:
        experiment = session.query(tm.Experiment).one()
        microscope_type = experiment.microscope_type
    imgfile_regex, metadata_regex = get_microscope_type_regex(microscope_type)

    # TODO: check if metadata files are missing
    is_valid = [check_file(f['name']) for f in data['files']]

    return jsonify({
        'is_valid': is_valid
    })


@api.route(
    '/experiments/<experiment_id>/acquisitions/<acquisition_id>/upload/upload-file',
    methods=['POST']
)
@jwt_required()
@decode_query_ids()
def upload_file(experiment_id, acquisition_id):
    """
    .. http:post:: /api/experiments/(string:experiment_id)/acquisitions/(string:acquisition_id)/upload/upload-file

        Upload a single file via HTTP.

        **Example response**:

        .. sourcecode:: http

            Content-Type: application/json

            {
                "message": "ok"
            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 400: malformed request or file not registered for upload
        :statuscode 500: server error during upload

    """
    # TODO: shouldn't this be a PUT request?
    f = request.files.get('file')

    # Get the file form the form
    if not f:
        raise MalformedRequestError('Missing file entry in the upload request.')

    with tm.utils.ExperimentSession(experiment_id) as session:
        acquisition = session.query(tm.Acquisition).get(acquisition_id)
        if acquisition.status == FileUploadStatus.COMPLETE:
            logger.info('acquisition already complete')
            return jsonify(message='Acquisition complete')

        filename = secure_filename(f.filename)
        imgfile = session.query(tm.MicroscopeImageFile).\
            filter_by(name=filename, acquisition_id=acquisition_id).\
            one_or_none()
        metafile = session.query(tm.MicroscopeMetadataFile).\
            filter_by(name=filename, acquisition_id=acquisition_id).\
            one_or_none()

        is_imgfile = imgfile is not None
        is_metafile = metafile is not None
        if not is_metafile and not is_imgfile:
            raise MalformedRequestError(
                'File was not registered: "%s"' % filename
            )
        elif is_imgfile:
            file_obj = imgfile
        elif is_metafile:
            file_obj = metafile
        else:
            raise MalformedRequestError(
                'File was registered as both image and metadata file: "%s"'
                % filename
            )

        # TODO: Status codes
        if file_obj.status == FileUploadStatus.COMPLETE:
            logger.info('file "%s" already uploaded')
            return jsonify(message='File already uploaded')
        elif file_obj.status == FileUploadStatus.UPLOADING:
            logger.info('file "%s" already uploading')
            return jsonify(message='File upload already in progress')

        logger.info('upload file "%s"', filename)
        file_obj.status = FileUploadStatus.UPLOADING
        session.add(file_obj)
        session.commit()

        try:
            f.save(file_obj.location)
            file_obj.status = FileUploadStatus.COMPLETE
        except Exception as error:
            file_obj.status = FileUploadStatus.FAILED
            raise InternalServerError(
                'Upload of file failed: %s' % str(error)
            )

    return jsonify(message='ok')


@api.route(
    '/experiments/<experiment_id>/acquisitions/<acquisition_id>/upload/count',
    methods=['GET']
)
@jwt_required()
@decode_query_ids()
def get_uploaded_file_count(experiment_id, acquisition_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/acquisitions/(string:acquisition_id)/upload/count

        Get the count of already uploaded files.

        **Example response**:

        .. sourcecode:: http

            Content-Type: application/json

            {
                "data": 132
            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error

    """
    with tm.utils.ExperimentSession(experiment_id) as session:
        acquisition = session.query(tm.Acquisition).get(acquisition_id)
        n_imgfiles = session.query(tm.MicroscopeImageFile).\
            filter_by(
                status=FileUploadStatus.COMPLETE, acquisition_id=acquisition_id
            ).\
            count()
        n_metafiles = session.query(tm.MicroscopeMetadataFile).\
            filter_by(
                status=FileUploadStatus.COMPLETE, acquisition_id=acquisition_id
            ).\
            count()
    return jsonify({
        'data': n_imgfiles + n_metafiles
    })

