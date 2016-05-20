import os.path as p
import json
import datetime
import importlib
import re

from flask import request
from flask.ext.jwt import jwt_required
from werkzeug import secure_filename

from tmlib.models import (
    Acquisition,
    MicroscopeImageFile,
    MicroscopeMetadataFile
)
from tmlib.models.status import FileUploadStatus
import tmlib.workflow.metaconfig

from tmaps.extensions import redis_store
from tmaps.api import api
from tmaps.extensions import db
from tmaps.util import (
    extract_model_from_path,
    extract_model_from_body
)
from tmaps.error import *


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
            'No files supplied. Cannot register upload.')

    # Delete any old files
    for f in acquisition.microscope_image_files:
        db.session.delete(f)
    for f in acquisition.microscope_metadata_files:
        db.session.delete(f)
    db.session.commit()

    # file_key = 'acquisition:%d:upload:files' % acquisition.id
    # registered_flag_key = 'acquisition:%d:upload:registered' % acquisition.id

    # redis_store.set(registered_flag_key, True)

    microscope_type = acquisition.plate.experiment.microscope_type
    metaconfig = importlib.import_module(
        'tmlib.workflow.metaconfig.%s' % microscope_type)
    imgfile_regex = re.compile(metaconfig.IMAGE_FILE_REGEX_PATTERN)
    metadata_regex = re.compile(metaconfig.METADATA_FILE_REGEX_PATTERN)

    imgfiles = [secure_filename(f) for f in data['files'] if imgfile_regex.match(f)]
    metafiles = [secure_filename(f) for f in data['files'] if metadata_regex.match(f)]

    imgfile_objects = \
        [MicroscopeImageFile(name=f, acquisition_id=acquisition.id)
         for f in imgfiles]
    metafile_objects = \
        [MicroscopeMetadataFile(name=f, acquisition_id=acquisition.id)
         for f in metafiles]

    db.session.add_all(imgfile_objects + metafile_objects)
    db.session.commit()

    # redis_store.delete(file_key)  # clear before adding
    # redis_store.sadd(file_key, *filenames)

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
    metaconfig = importlib.import_module(
        'tmlib.workflow.metaconfig.%s' % microscope_type)

    imgfile_regex = re.compile(metaconfig.IMAGE_FILE_REGEX_PATTERN)
    metadata_regex = re.compile(metaconfig.METADATA_FILE_REGEX_PATTERN)

    def check_file(fname):
        is_imgfile = imgfile_regex.match(fname) is not None
        is_metadata_file = metadata_regex.match(fname) is not None
        return is_metadata_file or is_imgfile

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
    # file_key = 'acquisition:%d:upload:files' % acquisition.id
    # registered_flag_key = 'acquisition:%d:upload:registered' % acquisition.id

    # is_registered = redis_store.get(registered_flag_key)

    # if not is_registered:
    #     acquisition.upload_status = FileUploadStatus.FAILED
    #     raise MalformedRequestError('No upload was registered for this acquisition.')
    # else:
    #     acquisition.upload_status = FileUploadStatus.UPLOADING
    if acquisition.status == FileUploadStatus.FAILED:
        raise InternalServerError(
            'One or more files in this upload failed. This upload has to be '
            'registered again before any upload attempt can be made again.')
    elif acquisition.status == FileUploadStatus.COMPLETE:
        raise MalformedRequestError(
            'No upload was registered for this acquisition.')

    # Get the file form the form
    f = request.files.get('file')
    if not f:
        raise MalformedRequestError('Missing file entry in this request.')

    # filename = secure_filename(f.filename)
    filename = f.filename
    imgfile_objs = [fl for fl in acquisition.microscope_image_files if fl.name == filename]
    metafile_objs = [fl for fl in acquisition.microscope_metadata_files if fl.name == filename]

    if len(imgfile_objs) > 1:
        raise MalformedRequestError('Multiple image files found with this name.')
    if len(metafile_objs) > 1:
        raise MalformedRequestError('Multiple metadata files found with this name.')

    is_imgfile = len(imgfile_objs) == 1
    is_metafile = len(metafile_objs) == 1
    if is_imgfile and is_metafile:
        raise MalformedRequestError('This file was registered as a metadata and as an image file.')
    if is_imgfile:
        file_obj = imgfile_objs[0]
    elif is_metafile:
        file_obj = metafile_objs[0]
    else:
        raise MalformedRequestError('This file was registered never registered.')

    f.save(file_obj.location)
    file_obj.upload_status = FileUploadStatus.COMPLETE

    # acquisition.save_microscope_image_file(f)
    # redis_store.srem(file_key, f.filename)

    # Check if this was the last upload
    # remaining_files = redis_store.smembers(file_key)
    # if len(remaining_files) == 0:
    #     acquisition.status = FileUploadStatus.COMPLETE

    db.session.commit()
    return jsonify(message='Upload ok')
