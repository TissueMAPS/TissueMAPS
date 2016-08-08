import os.path as p
import json
import datetime
import importlib
import logging
import re

from flask import request
from flask.ext.jwt import jwt_required
from werkzeug import secure_filename
from sqlalchemy.orm.exc import MultipleResultsFound

import tmlib.models as tm
from tmlib.models.status import FileUploadStatus
from tmlib.workflow.metaconfig import get_microscope_type_regex

from tmserver.extensions import redis_store
from tmserver.api import api
from tmserver.extensions import db
from tmserver.util import extract_model_from_path, assert_request_params
from tmserver.error import *

logger = logging.getLogger(__name__)


@api.route(
    '/experiments/<experiment_id>/acquisitions/<acquisition_id>/upload/register',
    methods=['PUT']
)
@jwt_required()
@assert_request_params('files')
@extract_model_from_path(tm.Experiment, tm.Acquisition, check_ownership=True)
def register_upload(experiment, acquisition):
    """
    Tell the server that an upload for this acquisition is imminent.
    The client should wait for this response before uploading files.

    Request
    -------

    {
        files: Array<string>
    }

    Response
    --------

    Response 200 or 500

    """
    data = request.get_json()

    if len(data.get('files', [])) == 0:
        raise MalformedRequestError(
            'No files supplied. Cannot register upload.'
        )

    microscope_type = acquisition.plate.experiment.microscope_type
    image_regex, metadata_regex = get_microscope_type_regex(microscope_type)

    image_filenames = [f.name for f in acquisition.microscope_image_files]
    valid_image_filenames = [
        f for f in data['files'] if image_regex.search(f)
    ]
    img_files = [
        tm.MicroscopeImageFile(
            name=secure_filename(f), acquisition_id=acquisition.id
        )
        for f in valid_image_filenames
        if secure_filename(f) not in image_filenames
    ]
    metadata_filenames = [f.name for f in acquisition.microscope_metadata_files]
    valid_metadata_filenames = [
        f for f in data['files'] if metadata_regex.search(f)
    ]
    meta_files = [
        tm.MicroscopeMetadataFile(
            name=secure_filename(f), acquisition_id=acquisition.id
        )
        for f in valid_metadata_filenames
        if secure_filename(f) not in metadata_filenames
    ]

    db.session.add_all(img_files + meta_files)
    db.session.commit()

    # Trigger creation of directories
    acquisition.location
    acquisition.microscope_images_location
    acquisition.microscope_metadata_location

    # NOTE: We have to return the original local filenames and not the ones
    # potentially modified by secure_filename()!
    return jsonify({
        'message': 'Ok',
        'data': valid_image_filenames + valid_metadata_filenames
    })


@api.route(
    '/experiments/<experiment_id>/acquisitions/<acquisition_id>/upload/validity-check',
    methods=['POST']
)
@jwt_required()
@assert_request_params('files')
@extract_model_from_path(tm.Experiment, tm.Acquisition, check_ownership=True)
def file_validity_check(experiment, acquisition):
    data = request.get_json()
    if not type(data['files']) is list:
        raise MalformedRequestError('No image files provided.')

    microscope_type = acquisition.plate.experiment.microscope_type
    imgfile_regex, metadata_regex = get_microscope_type_regex(microscope_type)

    def check_file(fname):
        is_imgfile = imgfile_regex.search(fname) is not None
        is_metadata_file = metadata_regex.search(fname) is not None
        return is_metadata_file or is_imgfile

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
@extract_model_from_path(tm.Experiment, tm.Acquisition, check_ownership=True)
def upload_file(experiment, acquisition):
    f = request.files.get('file')
    if acquisition.status == FileUploadStatus.COMPLETE:
        logger.info('acquisition already complete')
        return jsonify(message='Acquisition complete')

    # Get the file form the form
    if not f:
        raise MalformedRequestError('Missing file entry in this request.')

    filename = secure_filename(f.filename)
    imgfile = db.session.query(tm.MicroscopeImageFile).\
        filter_by(name=filename, acquisition_id=acquisition.id).\
        one_or_none()
    metafile = db.session.query(tm.MicroscopeMetadataFile).\
        filter_by(name=filename, acquisition_id=acquisition.id).\
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

    if file_obj.status == FileUploadStatus.COMPLETE:
        logger.debug('file "%s" already uploaded')
        return jsonify(message='File already uploaded')
    elif file_obj.status == FileUploadStatus.UPLOADING:
        logger.debug('file "%s" already uploading')
        return jsonify(message='File upload already in progress')

    logger.debug('upload file "%s"', filename)
    file_obj.status = FileUploadStatus.UPLOADING
    db.session.add(file_obj)
    db.session.commit()

    try:
        f.save(file_obj.location)
        file_obj.status = FileUploadStatus.COMPLETE
        db.session.add(file_obj)
        db.session.commit()
    except Exception as error:
        file_obj.status = FileUploadStatus.FAILED
        db.session.add(file_obj)
        db.session.commit()
        raise InternalServerError(
            'Upload of file failed: %s' % str(error)
        )

    return jsonify(message='Upload ok')
