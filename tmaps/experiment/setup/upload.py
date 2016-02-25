import os.path as p
import json
import datetime

from flask import request
from flask_jwt import jwt_required
from flask.ext.jwt import current_identity
from werkzeug import secure_filename

from tmaps.extensions.redis import redis_store
from tmaps.api import api

from tmaps.experiment.setup import PlateAcquisition
from tmaps.extensions.database import db
from tmaps.response import *


@api.route('/acquisitions/<int:aq_id>/register-upload',
                 methods=['PUT'])
@jwt_required()
def register_upload(aq_id):
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
    # 1) Create the plate directory if it doesn't exist already
    # 2) Save the plate upload directory in the db.
    data = json.loads(request.data)

    if data is None or len(data.get('files', [])) == 0:
        return MALFORMED_REQUEST_RESPONSE
    aq = PlateAcquisition.get(aq_id)
    if not aq:
        return RESOURCE_NOT_FOUND_RESPONSE

    aq.remove_files()

    file_key = 'acquisition:%d:upload:files' % aq_id
    registered_flag_key = 'acquisition:%d:upload:registered' % aq_id

    redis_store.set(registered_flag_key, True)

    filenames = [secure_filename(f) for f in data['files']]
    redis_store.delete(file_key)  # clear before adding
    redis_store.sadd(file_key, *filenames)

    return 'Upload registered', 200


@api.route('/acquisitions/<int:aq_id>/upload-file',
                 methods=['POST'])
@jwt_required()
def upload_file(aq_id):
    aq = PlateAcquisition.get(aq_id)
    if not aq:
        return RESOURCE_NOT_FOUND_RESPONSE

    file_key = 'acquisition:%d:upload:files' % aq_id
    registered_flag_key = 'acquisition:%d:upload:registered' % aq_id

    is_registered = redis_store.get(registered_flag_key)
    if not is_registered:
        aq.update(upload_status='FAILED')
        return MALFORMED_REQUEST_RESPONSE
    else:
        aq.update(upload_status='UPLOADING')

    # Get the file form the form
    f = request.files.get('file')
    if not f:
        aq.update(upload_status='FAILED')
        return MALFORMED_REQUEST_RESPONSE

    aq.save_file(f)
    redis_store.srem(file_key, f.filename)

    # Check if this was the last upload
    remaining_files = redis_store.smembers(file_key)
    if len(remaining_files) == 0:
        aq.update(upload_status='SUCCESSFUL')

    return 'Upload ok', 200


# @api.route('/acquisitions/<int:aq_id>/upload-status', methods=['GET'])
# @jwt_required()
# def get_upload_status(aq_id):
#     """
#     When GETing to this address, the server will respond as soon as all files
#     from the previous register step were uploaded.

#     """
#     file_key = 'acquisition:%d:upload:files' % aq_id
#     registered_flag_key = 'acquisition:%d:upload:registered' % aq_id

#     time_started = datetime.datetime.utcnow()
#     time_delta = datetime.timedelta(seconds=5)

#     while True:
#         now = datetime.datetime.utcnow()
#         if now - time_started > time_delta:
#             # Deregister experiment, this will cause all uploads to fail
#             # until a new upload is registered.
#             redis_store.set(registered_flag_key, False)
#             return 'Upload takes too long, aborting...', 500

#         remaining_files = redis_store.smembers(file_key)
#         # redis_store.publish('log', remaining_files)
#         if len(remaining_files) == 0:
#             redis_store.delete(file_key)
#             return 'All files uploaded', 200
