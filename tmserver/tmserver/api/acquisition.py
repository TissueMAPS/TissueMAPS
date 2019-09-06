# TmServer - TissueMAPS server application.
# Copyright (C) 2016-2019 University of Zurich.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""API view functions for querying :mod:`acquisition <tmlib.models.acquisition>`
resources.
"""
import json
import logging
import os
import re

import numpy as np
from flask import jsonify, send_file, request
from flask_jwt import jwt_required
from werkzeug import secure_filename

from tmlib.config import LibraryConfig
import tmlib.models as tm
from tmlib.models.status import FileUploadStatus
from tmlib.workflow.metaconfig import get_microscope_type_regex

from tmserver.util import (
    decode_query_ids, decode_form_ids, is_true, is_false,
    assert_query_params, assert_form_params
)
from tmserver.api import api
from tmserver.error import *

logger = logging.getLogger(__name__)


@api.route('/experiments/<experiment_id>/acquisitions', methods=['POST'])
@jwt_required()
@assert_form_params('plate_name', 'name')
@decode_query_ids('write')
@decode_form_ids()
def create_acquisition(experiment_id):
    """
    .. http:post:: /api/experiments/(string:experiment_id)/acquisitions

        Create a new :class:`Acquisition <tmlib.models.acquisition.Acquisition>`.

        **Example request**:

        .. sourcecode:: http

            Content-Type: application/json

            {
                "name": "Acquisition XY",
                "plate_name": "Plate XY"
            }

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": {
                    "id": "MQ==",
                    "name": "Plate XY",
                    "description": "Optional description"
                    "status": "WAITING"
                }
            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 404: no plate found under that name

    """
    data = request.get_json()
    plate_name = data.get('plate_name')
    name = data.get('name')
    desc = data.get('description', '')
    logger.info(
        'create acquisition "%s" for plate "%s" from experiment %d',
        name, plate_name, experiment_id
    )
    with tm.utils.ExperimentSession(experiment_id) as session:
        plate = session.query(tm.Plate).\
            filter_by(name=plate_name).\
            one_or_none()
        if plate is None:
            raise ResourceNotFoundError('Plate "%s" not found' % plate_name)
        acquisition = tm.Acquisition(
            name=name, description=desc, plate_id=plate.id
        )
        session.add(acquisition)
        session.commit()
        return jsonify(data=acquisition)


@api.route(
    '/experiments/<experiment_id>/acquisitions/<acquisition_id>',
    methods=['DELETE']
)
@jwt_required()
@decode_query_ids('write')
def delete_acquisition(experiment_id, acquisition_id):
    """
    .. http:delete:: /api/experiments/(string:experiment_id)/acquisitions/(string:acquisition_id)

        Delete a specific
        :class:`Acquisition <tmlib.models.acquisition.Acquisition>`.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "message": "ok"
            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 401: not authorized

    """
    logger.info(
        'delete acquisition %d from experiment %d',
        acquisition_id, experiment_id
    )
    with tm.utils.ExperimentSession(experiment_id) as session:
        session.query(tm.Acquisition).filter_by(id=acquisition_id).delete()
        # TODO: DELETE CASCADE mapobjects, channel_layer_tiles
    return jsonify(message='ok')


@api.route(
    '/experiments/<experiment_id>/acquisitions/<acquisition_id>',
    methods=['PUT']
)
@jwt_required()
@assert_form_params('name')
@decode_query_ids('write')
def update_acquisition(experiment_id, acquisition_id):
    """
    .. http:put:: /api/experiments/(string:experiment_id)/acquisitions/(string:acquisition_id)

        Update an :class:`Acquisition <tmlib.models.acquisition.Acquisition>`.

        **Example request**:

        .. sourcecode:: http

            Content-Type: application/json

            {
                "name": "New Name"
            }

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "message": "ok"
            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 400: malformed request
        :statuscode 200: no error

    """
    data = request.get_json()
    name = data.get('name')
    logger.info(
        'rename acquisition %d of experiment %d', acquisition_id, experiment_id
    )
    with tm.utils.ExperimentSession(experiment_id) as session:
        acquisition = session.query(tm.Acquisition).get(acquisition_id)
        acquisition.name = name
    return jsonify(message='ok')



@api.route('/experiments/<experiment_id>/acquisitions', methods=['GET'])
@jwt_required()
@decode_query_ids('read')
def get_acquisitions(experiment_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/acquisitions

        Get acquisitions for the specified experiment.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": [
                    {
                        "id": "MQ==",
                        "name": "Acquisition XY",
                        "description": "",
                        "status": "UPLOADING" | "COMPLETE" | "WAITING"
                    },
                    ...
                ]
            }

        :query plate_name: name of a parent plate (optional)
        :query name: name of an acquistion (optional)

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 404: no such experiment found

    """
    plate_name = request.args.get('plate_name')
    acquisition_name = request.args.get('name')
    logger.info('get acquistions for experiment %d', experiment_id)
    with tm.utils.ExperimentSession(experiment_id) as session:
        acquisitions = session.query(tm.Acquisition)
        if acquisition_name is not None:
            acquisitions = acquisitions.\
                filter_by(name=acquisition_name)
        if plate_name is not None:
            acquisitions = acquisitions.\
                join(tm.Plate).\
                filter(tm.Plate.name == plate_name)
        return jsonify({
            'data': acquisitions.all()
        })


@api.route(
    '/experiments/<experiment_id>/acquisitions/<acquisition_id>',
    methods=['GET']
)
@jwt_required()
@decode_query_ids('read')
def get_acquisition(experiment_id, acquisition_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/acquisitions/(string:acquisition_id)

        Get a specific acquisition object.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": {
                    "id": "MQ==",
                    "name": "Acquisition XY",
                    "description": "",
                    "status": "UPLOADING" | "COMPLETE" | "WAITING"
                }
            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 404: no acquisition found with that id

    """
    logger.info(
        'get acquisition %d of experiment %d', acquisition_id, experiment_id
    )
    with tm.utils.ExperimentSession(experiment_id) as session:
        acquisition = session.query(tm.Acquisition).get(acquisition_id)
        return jsonify(data=acquisition)

@api.route(
    '/experiments/<experiment_id>/acquisitions/<acquisition_id>/register',
    methods=['POST']
)
@jwt_required()
@assert_form_params('path')
@decode_query_ids('write')
def register(experiment_id, acquisition_id):
    """
    .. http:post:: /api/experiments/(string:experiment_id)/acquisitions/(string:acquisition_id)/register

        Register a single directory (passed as parameter `path` in the
        JSON request) as the directory containing all the files for
        the given acquisition.

        Calling this method twice with different `path` parameters
        will result in an error (so you cannot combine the contents of
        two directories by 'registering' them).  On the other hand,
        the *same* directory can be registered over and over again
        without adverse side-effects; the method is idempotent in this
        sense.

        **Example request**:

        .. sourcecode:: http

            Content-Type: application/json

            {
                "path": "/fullpath/to/serversidedata"
            }

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": "/fullpath/to/serversidedata"
            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 500: server error
    """
    data = request.get_json()
    path = data['path']
    logger.info('Registering microscope files from path `%s` ...', path)

    if not os.path.isabs(path):
        raise MalformedRequestError("Cannot register relative paths.")

    if not os.path.isdir(path):
        raise MalformedRequestError(
            "Path `{}` is not an existing directory on this TM server"
            .format(path)
        )

    try:
        filenames = [
            f for f in os.listdir(path)
            if (not f.startswith('.')
                and not os.path.isdir(os.path.join(path, f)))
        ]
    except OSError as err:
        msg = "Cannot list directory `{}`: {}".format(path, err)
        logger.error(msg)
        raise MalformedRequestError(msg)

    with tm.utils.ExperimentSession(experiment_id) as session:
        experiment = session.query(tm.Experiment).one()
        microscope_type = experiment.microscope_type
        img_regex, metadata_regex = get_microscope_type_regex(microscope_type)
        acquisition = session.query(tm.Acquisition).get(acquisition_id)
        plate = session.query(tm.Plate).get(acquisition.plate_id)

        # check for image files already registered
        img_filenames = [f.name for f in acquisition.microscope_image_files]
        img_files = [
            tm.MicroscopeImageFile(
                name=f, acquisition_id=acquisition.id
            )
            for f in filenames
            if img_regex.search(f) and
            f not in img_filenames
        ]
        # check for metadata already registered
        meta_filenames = [f.name for f in acquisition.microscope_metadata_files]
        meta_files = [
            tm.MicroscopeMetadataFile(
                name=secure_filename(f), acquisition_id=acquisition.id
            )
            for f in filenames
            if metadata_regex.search(f) and
            f not in meta_filenames
        ]

        session.bulk_save_objects(img_files + meta_files)

        # trigger creation of directories
        acquisition.location
        acquisition.microscope_metadata_location

        # link root directory
        path_to_link = os.path.join(
            LibraryConfig().storage_home,
            ('experiment_{}'
             '/plates/plate_{}'
             '/acquisitions/acquisition_{}'
             '/microscope_images'
            .format(experiment.id, plate.id, acquisition.id)))
        if not os.path.exists(path_to_link):
            try:
                os.symlink(path, path_to_link)
            except Exception as err:
                logger.error(
                    "Error linking source directory `%s` to TM directory `%s`: %s",
                    path, path_to_link, err)
                raise
        else:
            # path exists, check if it is correct
            p1 = os.path.realpath(path)
            p2 = os.path.realpath(path_to_link)
            if p1 != p2:
                raise ValueError(
                    "Acquisition {a} of plate {p} of experiment {e}"
                    " is already linked to directory `{d}`"
                    .format(
                        a=acquisition.id,
                        p=plate.id,
                        e=experiment.id,
                        d=p1))

        microscope_files = session.query(tm.MicroscopeImageFile).filter_by(acquisition_id=acquisition.id).all()
        for microscope_file in microscope_files:
            microscope_file.location
            microscope_file.status = 'COMPLETE'

    return jsonify(message='ok')




@api.route(
    '/experiments/<experiment_id>/acquisitions/<acquisition_id>/upload/register',
    methods=['POST']
)
@jwt_required()
@assert_form_params('files')
@jwt_required()
@decode_query_ids('write')
def register_upload(experiment_id, acquisition_id):
    """
    .. http:post:: /api/experiments/(string:experiment_id)/acquisitions/(string:acquisition_id)/upload/register

        Notify the server that an upload for this acquisition is imminent.
        The client has to wait for this response before uploading files.

        **Example request**:

        .. sourcecode:: http

            Content-Type: application/json

            {
                "files": ["file1.png", "file2.png", ...]
            }

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": ["file1.png", "file2.png", ...]
            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 500: server error

    """
    logger.info('register microscope files for upload')
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
        image_filenames = session.query(tm.MicroscopeImageFile.name).\
            filter(tm.MicroscopeImageFile.status != FileUploadStatus.COMPLETE).\
            all()
        metadata_filenames = session.query(tm.MicroscopeMetadataFile.name).\
            filter(tm.MicroscopeMetadataFile.status != FileUploadStatus.COMPLETE).\
            all()
        all_filenames = image_filenames + metadata_filenames
        logger.info('registered %d files', len(all_filenames))
        return jsonify(data=[f.name for f in all_filenames])


@api.route(
    '/experiments/<experiment_id>/acquisitions/<acquisition_id>/upload/validity-check',
    methods=['POST']
)
@jwt_required()
@assert_form_params('files')
@decode_query_ids('write')
def check_file_validity(experiment_id, acquisition_id):
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
    logger.info('check whether files are valid for upload')
    data = json.loads(request.data)
    if not 'files' in data:
        raise MalformedRequestError()
    if not type(data['files']) is list:
        raise MalformedRequestError('No image files provided.')

    with tm.utils.ExperimentSession(experiment_id) as session:
        experiment = session.query(tm.Experiment).one()
        microscope_type = experiment.microscope_type
    imgfile_regex, metadata_regex = get_microscope_type_regex(microscope_type)

    def check_file(fname):
        is_imgfile = imgfile_regex.search(fname) is not None
        is_metadata_file = metadata_regex.search(fname) is not None
        return is_metadata_file or is_imgfile

    # TODO: check if metadata files are missing
    is_valid = [check_file(f['name']) for f in data['files']]

    logger.info('%d of %d files are valid', np.sum(is_valid), len(is_valid))

    return jsonify({
        'is_valid': is_valid
    })


@api.route(
    '/experiments/<experiment_id>/acquisitions/<acquisition_id>/microscope-file',
    methods=['POST']
)
@jwt_required()
@decode_query_ids('write')
def add_microcope_file(experiment_id, acquisition_id):
    """
    .. http:post:: /api/experiments/(string:experiment_id)/acquisitions/(string:acquisition_id)/microscope-file

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
            logger.warn('skip file that was not registered: "%s"' % filename)
            return jsonify(message='non-registered file: skipped')
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
            logger.info('file "%s" already uploaded', filename)
            return jsonify(message='File already uploaded')
        elif file_obj.status == FileUploadStatus.UPLOADING:
            logger.info('file "%s" already uploading', filename)
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
@decode_query_ids('write')
def get_uploaded_file_count(experiment_id, acquisition_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/acquisitions/(string:acquisition_id)/upload/count

        Get the number of successfully uploaded microscope files for the
        specified :class:`Acquisition <tmlib.models.acquisition.Acquisition>`.

        **Example response**:

        .. sourcecode:: http

            Content-Type: application/json

            {
                "data": 132
            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error

    """
    logger.info(
        'get number of uploaded files for acquisition %d of experiment %d',
        acquisition_id, experiment_id
    )
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


@api.route(
    '/experiments/<experiment_id>/acquisitions/<acquisition_id>/images',
    methods=['GET']
)
@jwt_required()
@decode_query_ids('read')
def get_microscope_image_file_information(experiment_id, acquisition_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/acquisitions/(string:acquisition_id)/images

        Get information about image files registerd for the specified
        :class:`Acquisition <tmlib.models.acquisition.Acquisition>`

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": [
                    {
                        "name": "some-file-name.png",
                        "status": "UPLOADING" | "WAITING" | "COMPLETE" | "FAILED"
                    },
                    ...
                ]
            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 404: no matching acquisition found

    """
    logger.info(
        'get microscope image files for acquisition %d from experiment %d',
        acquisition_id, experiment_id
    )
    with tm.utils.ExperimentSession(experiment_id) as session:
        acquisition = session.query(tm.Acquisition).get(acquisition_id)
        return jsonify({
            'data': acquisition.microscope_image_files
        })


@api.route(
    '/experiments/<experiment_id>/acquisitions/<acquisition_id>/metadata',
    methods=['GET']
)
@jwt_required()
@decode_query_ids('read')
def get_microscope_metadata_file_information(experiment_id, acquisition_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/acquisitions/(string:acquisition_id)/metadata

        Get information about metadata files registered for the specified
        :class:`Acquisition <tmlib.models.acquisition.Acquisition>`

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": [
                    {
                        "name": "some-file-name.png",
                        "status": "UPLOADING" | "WAITING" | "COMPLETE" | "FAILED"
                    },
                    ...
                ]
            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 404: no matching acquisition found

    """
    logger.info(
        'get microscope metadata files for acquisition %d from experiment %d',
        acquisition_id, experiment_id
    )
    with tm.utils.ExperimentSession(experiment_id) as session:
        acquisition = session.query(tm.Acquisition).get(acquisition_id)
        return jsonify({
            'data': acquisition.microscope_metadata_files
        })
