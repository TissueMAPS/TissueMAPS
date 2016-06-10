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

from tmlib.models import (
    Acquisition,
    MicroscopeImageFile,
    MicroscopeMetadataFile
)
from tmlib.models.status import FileUploadStatus
from tmlib.workflow.metaconfig import get_microscope_type_regex

from tmaps.extensions import redis_store
from tmaps.api import api
from tmaps.extensions import db
from tmaps.util import (
    extract_model_from_path,
    extract_model_from_body
)
from tmaps.error import *

logger = logging.getLogger(__name__)


@api.route('/acquisitions/<acquisition_id>/register-upload',
                 methods=['PUT'])
@jwt_required()
@extract_model_from_path(Acquisition, check_ownership=True)
def register_upload(acquisition):
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
    data = json.loads(request.data)

    if data is None or len(data.get('files', [])) == 0:
        raise MalformedRequestError(
            'No files supplied. Cannot register upload.'
        )

    microscope_type = acquisition.plate.experiment.microscope_type
    imgfile_regex, metadata_regex = get_microscope_type_regex(microscope_type)

    img_filenames = [f.name for f in acquisition.microscope_image_files]
    img_files = [
        MicroscopeImageFile(
            name=secure_filename(f), acquisition_id=acquisition.id
        )
        for f in data['files']
        if imgfile_regex.match(f) and f not in img_filenames
    ]
    meta_filenames = [f.name for f in acquisition.microscope_metadata_files]
    meta_files = [
        MicroscopeMetadataFile(
            name=secure_filename(f), acquisition_id=acquisition.id
        )
        for f in data['files']
        if metadata_regex.match(f) and f not in meta_filenames
    ]

    db.session.add_all(img_files + meta_files)
    db.session.commit()

    # Trigger creation of directories
    acquisition.location
    acquisition.microscope_images_location
    acquisition.microscope_metadata_location

    return jsonify(message='Upload registered')


@api.route('/acquisitions/<acquisition_id>/file-validity-check', methods=['POST'])
@jwt_required()
@extract_model_from_path(Acquisition, check_ownership=True)
def file_validity_check(acquisition):
    data = json.loads(request.data)
    if not 'files' in data:
        raise MalformedRequestError()
    if not type(data['files']) is list:
        raise MalformedRequestError()

    microscope_type = acquisition.plate.experiment.microscope_type
    imgfile_regex, metadata_regex = get_microscope_type_regex(microscope_type)

    def check_file(fname):
        is_imgfile = imgfile_regex.match(fname) is not None
        is_metadata_file = metadata_regex.match(fname) is not None
        return is_metadata_file or is_imgfile

    # TODO: check if metadata files are missing
    data = json.loads(request.data)
    filenames = [f['name'] for f in data['files']]
    is_valid = map(check_file, filenames)

    return jsonify({
        'is_valid': is_valid
    })


@api.route('/acquisitions/<acquisition_id>/upload-file', methods=['POST'])
@jwt_required()
@extract_model_from_path(Acquisition, check_ownership=True)
def upload_file(acquisition):
    f = request.files.get('file')
    if acquisition.status == FileUploadStatus.COMPLETE:
        logger.info('acquisition already complete')
        return jsonify(message='Acquisition complete')

    # Get the file form the form
    if not f:
        raise MalformedRequestError('Missing file entry in this request.')

    # filename = secure_filename(f.filename)
    filename = f.filename
    imgfile = db.session.query(MicroscopeImageFile).\
        filter_by(name=filename, acquisition_id=acquisition.id).\
        one_or_none()
    metafile = db.session.query(MicroscopeMetadataFile).\
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

    if file_obj.upload_status == FileUploadStatus.COMPLETE:
        logger.info('file "%s" already uploaded')
        return jsonify(message='File already uploaded')
    elif file_obj.upload_status == FileUploadStatus.UPLOADING:
        logger.info('file "%s" already uploading')
        return jsonify(message='File upload already in progress')

    logger.info('upload file "%s"', filename)
    file_obj.upload_status = FileUploadStatus.UPLOADING
    db.session.add(file_obj)
    db.session.commit()

    try:
        f.save(file_obj.location)
        file_obj.upload_status = FileUploadStatus.COMPLETE
        db.session.add(file_obj)
        db.session.commit()
    except Exception as error:
        file_obj.upload_status = FileUploadStatus.FAILED
        db.session.add(file_obj)
        db.session.commit()
        raise InternalServerError(
            'Upload of file failed: %s' % str(error)
        )

    return jsonify(message='Upload ok')
