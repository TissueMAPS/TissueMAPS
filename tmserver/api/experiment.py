# TmServer - TissueMAPS server application.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
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
"""API view functions for experiment and related resources."""
import json
import os
from cStringIO import StringIO
import logging
import numpy as np
from flask import jsonify, send_file, current_app, request
from flask_jwt import jwt_required
from flask_jwt import current_identity
from werkzeug import secure_filename

import tmlib.models as tm
from tmlib.image import PyramidTile
from tmlib.logging_utils import LEVELS_TO_VERBOSITY
from tmlib.workflow.metaconfig import SUPPORTED_MICROSCOPE_TYPES
from tmlib.models.plate import SUPPORTED_PLATE_AQUISITION_MODES
from tmlib import cfg as lib_cfg

from tmserver.util import decode_query_ids, decode_form_ids
from tmserver.util import assert_query_params, assert_form_params
from tmserver.model import decode_pk
from tmserver.model import encode_pk
from tmserver.api import api
from tmserver.error import (
    MalformedRequestError,
    MissingGETParameterError,
    MissingPOSTParameterError,
    ResourceNotFoundError,
    NotAuthorizedError
)
from tmserver import cfg as server_cfg


logger = logging.getLogger(__name__)

def _raise_error_when_missing(arg):
    raise MissingGETParameterError(arg)

@api.route(
    '/experiments/<experiment_id>/channel_layers/<channel_layer_id>/tiles',
    methods=['GET']
)
@assert_query_params('x', 'y', 'z')
@decode_query_ids()
def get_channel_layer_tile(experiment_id, channel_layer_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/channel_layer/(string:channel_layer_id)/tiles

        Sends a pyramid tile image for a specific channel layer.

        :query x: zero-based `x` coordinate
        :query y: zero-based `y` coordinate
        :query z: zero-based zoom level index

    """
    logger.info(
        'get tile for channel layer %d of experiment %d',
        channel_layer_id, experiment_id
    )
    x = request.args.get('x', type=int)
    y = request.args.get('y', type=int)
    z = request.args.get('z', type=int)

    with tm.utils.ExperimentSession(experiment_id) as session:
        channel_layer = session.query(tm.ChannelLayer).get(channel_layer_id)
        logger.debug(
            'get channel layer tile: x=%d, y=%d, z=%d, zplane=%d, tpoint=%d',
            x, y, z, channel_layer.zplane, channel_layer.tpoint
        )

        channel_layer_tile = session.query(tm.ChannelLayerTile).\
            filter_by(
                column=x, row=y, level=z,
                channel_layer_id=channel_layer.id
            ).\
            one_or_none()

        if channel_layer_tile is None:
            logger.warn('tile does not exist - create empty')
            tile = PyramidTile.create_as_background()
            pixels = tile.jpeg_encode()
        else:
            pixels = channel_layer_tile._pixels
        f = StringIO()
        f.write(pixels)
        f.seek(0)
        return send_file(f, mimetype='image/jpeg')


@api.route('/experiments/<experiment_id>/cycles/id', methods=['GET'])
@jwt_required()
@assert_query_params('plate_name', 'cycle_index')
@decode_query_ids()
def get_cycle_id(experiment_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/cycles/id

        Get the hashed database id of a cycle with a given index and plate name.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "id": "MQ=="
            }

        :query plate_name: the name of the plate (required)
        :query cycle_index: the cycle's index (required)

        :statuscode 200: no error
        :statuscode 404: no matching cycle found

    """
    logger.info('get ID of cycle from experiment %d', experiment_id)
    experiment_name = experiment.name
    plate_name = request.args.get('plate_name')
    cycle_index = request.args.get('cycle_index', type=int)
    with tm.utils.ExperimentSession(experiment_id) as session:
        cycle = session.query(tm.Cycle).\
            join(tm.Plate).\
            filter(
                tm.Plate.name == plate_name,
                tm.Cycle.index == cycle_index,
            ).\
            one()
        return jsonify({
            'id': encode_pk(cycle.id)
        })


@api.route('/experiments/<experiment_id>/channels', methods=['GET'])
@jwt_required()
@decode_query_ids()
def get_channels(experiment_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/channels

        Get all channels for a specific experiment.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": [
                    {
                        "id": "MQ==",
                        "name": "Channel 1",
                        "bit_depth": 8,
                        "layers": [
                            {
                                "id": "MQ==",
                                "max_zoom": 12,
                                "tpoint": 0,
                                "zplane": 0,
                                "max_intensity": 6056,
                                "min_intensity": 0,
                                "experiment_id": "MQ==",
                                "image_size": {
                                    "width": 22000,
                                    "height": 10000
                                }
                            },
                            ...
                        ]
                    },
                    ...
                ]
            }

        :statuscode 200: no error

    """
    logger.info('get all channels from experiment %d', experiment_id)
    with tm.utils.ExperimentSession(experiment_id) as session:
        channels = session.query(tm.Channel).all()
        return jsonify(data=channels)


@api.route('/experiments/<experiment_id>/mapobject_types', methods=['GET'])
@jwt_required()
@decode_query_ids()
def get_mapobject_types(experiment_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/mapobject_types

        Get the supported mapobject types for a specific experiment.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": [
                    {
                        "id": "MQ==",
                        "name": "Cells",
                        "features": [
                            {
                                "id": "MQ==",
                                "name": "Cell_Area"
                            },
                            ...
                        ]
                    },
                    ...
                ]
            }

        :statuscode 200: no error

    """
    logger.info('get all mapobject types from experiment %d', experiment_id)
    with tm.utils.ExperimentSession(experiment_id) as session:
        mapobject_types = session.query(tm.MapobjectType).all()
        return jsonify(data=mapobject_types)


@api.route('/experiments/<experiment_id>/channels/id', methods=['GET'])
@jwt_required()
@assert_query_params('channel_name')
@decode_query_ids()
def get_channel_id(experiment_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/channels/id

        Get the id of a channel given its parent experiment id and its name.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "id": "MQ=="
            }

        :query channel_name: the name of the channel (required)

        :statuscode 200: no error
        :statuscode 404: no matching channel found

    """
    logger.info('get ID of channel from experiment %d', experiment_id)
    channel_name = request.args.get('channel_name')
    with tm.utils.ExperimentSession(experiment_id) as session:
        channel = session.query(tm.Channel).\
            filter_by(name=channel_name).\
            one()
        return jsonify({
            'id': encode_pk(channel.id)
        })


@api.route('/experiments/<experiment_id>/channel_layers/id', methods=['GET'])
@jwt_required()
@assert_query_params('channel_name', 'tpoint', 'zplane')
@decode_query_ids()
def get_channel_layer_id(experiment_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/channel_layers/id

        Get the id of a channel layer given its parent experiment id, the associated channel's name as well as the specific time point and zplane.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "id": "MQ=="
            }

        :query channel_name: the name of the channel (required)
        :query tpoint: the time point associated with this layer (required)
        :query zplane: the zplane of this layer (required)

        :statuscode 200: no error
        :statuscode 404: no matching layer found

    """
    logger.info('get ID of channel layer from experiment %d', experiment_id)
    channel_name = request.args.get('channel_name')
    tpoint = request.args.get('tpoint', type=int)
    zplane = request.args.get('zplane', type=int)
    with tm.utils.ExperimentSession(experiment_id) as session:
        channel_layer = session.query(tm.ChannelLayer).\
            join(tm.Channel).\
            filter(
                tm.Channel.name == channel_name,
                tm.ChannelLayer.tpoint == tpoint,
                tm.ChannelLayer.zplane == zplane,
            ).\
            one()
        return jsonify({
            'id': encode_pk(channel_layer.id)
        })


@api.route(
    '/experiments/<experiment_id>/channels/<channel_name>/image-files',
    methods=['GET']
)
@jwt_required()
@assert_query_params(
    'plate_name', 'cycle_index', 'well_name', 'x', 'y', 'tpoint', 'zplane'
)
@decode_query_ids()
def get_channel_image(experiment_id, channel_name):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/channels/(string:channel_name)/image-files

        Get a specific image belonging to a channel.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: image/png

        :query plate_name: the name of the plate (required)
        :query cycle_index: the cycle's index (required)
        :query well_name: the name of the well (required)
        :query x: the x-coordinate (required)
        :query y: the y-coordinate (required)
        :query tpoint: the time point (required)
        :query zplane: the z-plane (required)

        :statuscode 200: no error
        :statuscode 404: no matching image found
        :statuscode 400: not all query parameters provided

    """
    logger.info(
        'get image of channel "%s" from experiment %d',
        channel_name, experiment_id
    )
    plate_name = request.args.get('plate_name')
    well_name = request.args.get('well_name')
    x = request.args.get('x', type=int)
    y = request.args.get('y', type=int)
    cycle_index = request.args.get('cycle_index', type=int)
    tpoint = request.args.get('tpoint', type=int)
    zplane = request.args.get('zplane', type=int)
    illumcorr = request.args.get('correct', type=bool)
    with tm.utils.MainSession() as session:
        experiment = session.query(tm.ExperimentReference).get(experiment_id)
        experiment_name = experiment.name
    with tm.utils.ExperimentSession(experiment_id) as session:
        site_id = session.query(tm.Site.id).\
            join(tm.Well).\
            join(tm.Plate).\
            filter(
                tm.Plate.name == plate_name,
                tm.Well.name == well_name,
                tm.Site.x == x, tm.Site.y == y
            ).\
            one()[0]
        channel_id = session.query(tm.Channel.id).\
            filter_by(name=channel_name).\
            one()[0]
        image_file = session.query(tm.ChannelImageFile).\
            join(tm.Cycle).\
            filter(
                tm.Cycle.index == cycle_index,
                tm.ChannelImageFile.site_id == site_id,
                tm.ChannelImageFile.channel_id == channel_id,
                tm.ChannelImageFile.tpoint == tpoint
            ).\
            one()
        img = image_file.get(zplane)
        if illumcorr:
            # TODO: cache in Redis for a limited amount of time to not having to
            # load the file repeatedly when user downloads multiple files of the
            # same channel
            logger.info('correct image for illumination artefacts')
            illumstats_file = session.query(tm.IllumstatsFile).\
                filter_by(channel_id=channel_id, cycle_id=image_file.cycle_id).\
                one_or_none()
            if illumstats_file is None:
                raise ResourceNotFoundError(
                    'No illumination statistics file found for channel %d'
                    % channel_id
                )
            stats = illumstats_file.get()
            img = img.correct(stats)
    img = img.align()
    f = StringIO()
    f.write(img.png_encode())
    f.seek(0)
    filename = '%s_%s_x%.3d_y%.3d_z%.3d_t%.3d_%s.png' % (
        experiment_name, well_name, x, y, zplane, tpoint, channel_name
    )
    return send_file(
        f,
        attachment_filename=secure_filename(filename),
        mimetype='image/png',
        as_attachment=True
    )


@api.route('/microscope_types', methods=['GET'])
@jwt_required()
def get_microscope_types():
    """
    .. http:get:: /api/microscope_types

        Get a list of all supported microscope types for which images can be processed.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": [
                    "visiview", "cellvoyager", "axio", "default",
                    "metamorph", "niselements", "incell", "imc"
                ]
            }

        :statuscode 200: no error

        .. seealso::

            :class:`tmlib.workflow.metaconfig.SUPPORTED_MICROSCOPE_TYPES`

    """
    logger.info('get list of implemented microscope types')
    return jsonify({
        'data': list(SUPPORTED_MICROSCOPE_TYPES)
    })


@api.route('/acquisition_modes', methods=['GET'])
@jwt_required()
def get_acquisition_modes():
    """
    .. http:get:: /api/acquisition_modes

        Get a list of all implemented plate acquisition modes.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": ["basic", "multiplexing"]
            }

        :statuscode 200: no error

        .. seealso::

            :class:`tmlib.models.plate.SUPPORTED_PLATE_AQUISITION_MODES`

    """
    logger.info('get list of supported plate acquisition modes')
    return jsonify({
        'data': list(SUPPORTED_PLATE_AQUISITION_MODES)
    })


@api.route('/experiments', methods=['GET'])
@jwt_required()
def get_experiments():
    """
    .. http:get:: /api/experiments/(string:experiment_id)

        Get all experiments for the currently logged in user.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": [
                    {
                        "id": "MQ==",
                        "name": "Experiment XY",
                        "description": "Optional experiment description",
                        "user": "Testuser"
                    },
                    ...
                ]
            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 404: no such experiment found

    """
    logger.info('get all experiments')
    with tm.utils.MainSession() as session:
        experiments = session.query(tm.ExperimentReference).\
            filter_by(user_id=current_identity.id).\
            all()
        return jsonify({
            'data': experiments
        })


@api.route('/experiments/<experiment_id>', methods=['GET'])
@jwt_required()
@decode_query_ids()
def get_experiment(experiment_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)

        Get the experiment with the hashed id ``experiment_id``.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": {
                    "id": "MQ==",
                    "name": "Experiment XY",
                    "description": "Optional experiment description",
                    "user": "Testuser"
                }
            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 404: no such experiment found

    """
    logger.info('get experiment %d', experiment_id)
    with tm.utils.MainSession() as session:
        experiment = session.query(tm.ExperimentReference).get(experiment_id)
        return jsonify({
            'data': experiment
        })


@api.route('/experiments/id', methods=['GET'])
@jwt_required()
@assert_query_params('experiment_name')
def get_experiment_id():
    """
    .. http:get:: /api/experiments/(string:experiment_id)

        Get an experiment's id given its name.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "id": "MQ=="
            }

        :query experiment_name: the experiment's name (required)

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 404: no such experiment found

    """
    experiment_name = request.args.get('experiment_name')
    logger.info('get ID of experiment "%s"', experiment_name)
    with tm.utils.MainSession() as session:
        experiment = session.query(tm.ExperimentReference).\
            filter_by(user_id=current_identity.id, name=experiment_name).\
            one()
        return jsonify({
            'id': encode_pk(experiment.id)
        })


@api.route('/experiments', methods=['POST'])
@jwt_required()
@assert_form_params(
    'name', 'microscope_type', 'plate_format', 'plate_acquisition_mode'
)
def create_experiment():
    """
    .. http:post:: /api/experiments

        Create a new experiment.

        **Example request**:

        .. sourcecode:: http

            Content-Type: application/json

            {
                "name": "Experiment XY",
                "description": "Optional description",
                "plate_format": "0",
                "plate_acquisition_mode": "multiplexing",
                "microscope_type": "cellvoyager"
            }

        **Example response**:

        .. sourcecode:: http

            Content-Type: application/json

            {
                "id": "MQ==",
                "name": "Experiment XY",
                "description": "Optional description",
                "user": "Testuser"
            }

        :statuscode 200: no error

    """
    data = request.get_json()
    name = data.get('name')
    microscope_type = data.get('microscope_type')
    plate_format = int(data.get('plate_format'))
    plate_acquisition_mode = data.get('plate_acquisition_mode')
    description = data.get('description', '')
    logger.info('create experiment "%s"', name)
    with tm.utils.MainSession() as session:
        experiment_ref = tm.ExperimentReference(
            name=name,
            description=description,
            user_id=current_identity.id,
            root_directory=lib_cfg.storage_home
        )
        # TODO: raise error with meaningfull message in case of integrity error
        session.add(experiment_ref)
        session.commit()
        experiment_id = experiment_ref.id
        experiment_location = experiment_ref.location

    with tm.utils.ExperimentSession(experiment_id) as session:
        experiment = tm.Experiment(
            location=experiment_location,
            microscope_type=microscope_type,
            plate_format=plate_format,
            plate_acquisition_mode=plate_acquisition_mode
        )
        session.add(experiment)

    return jsonify({
        'data': {
            'id': experiment_id,
            'name': name,
            'description': description,
            'user': current_identity.name
        }
    })



@api.route('/experiments/<experiment_id>', methods=['DELETE'])
@jwt_required()
@decode_query_ids()
def delete_experiment(experiment_id):
    """
    .. http:delete:: /api/experiments/(string:experiment_id)

        Delete a specific experiment.

        **Example response**:

        .. sourcecode:: http

            Content-Type: application/json

            {
                "message": "ok"
            }

        :statuscode 200: no error

    """
    logger.info('delete experiment %d', experiment_id)
    with tm.utils.MainSession() as session:
        session.query(tm.ExperimentReference).\
            filter_by(id=experiment_id).\
            delete()
    return jsonify(message='ok')


@api.route('/experiments/<experiment_id>/plates/<plate_id>', methods=['GET'])
@jwt_required()
@decode_query_ids()
def get_plate(experiment_id, plate_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/plates/(string:plate_id)

        Get a plate given its id and the it of its parent experiment.

        **Example response**:

        .. sourcecode:: http

            Content-Type: application/json

            {
                "data": {
                    "id": "MQ==",
                    "name": "Plate XY",
                    "description": "Optional description",
                    "acquisitions": [
                        {
                            "id": "MQ==",
                            "name": "Acquisition XY",
                            "description": "",
                            "status": "UPLOADING" | "COMPLETE" | "WAITING"
                        },
                        ...
                    ],
                    "status": "UPLOADING" | "COMPLETE" | "WAITING"
                }
            }

        :statuscode 200: no error
        :statuscode 404: no such plate or experiment

    """
    logger.info('get plate %d from experiment %d', plate_id, experiment_id)
    with tm.utils.ExperimentSession(experiment_id) as session:
        plate = session.query(tm.Plate).get(plate_id)
        return jsonify(data=plate)


@api.route('/experiments/<experiment_id>/plates', methods=['GET'])
@jwt_required()
@decode_query_ids()
def get_plates(experiment_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/plates

        Get all plates for the specified experiment.

        **Example response**:

        .. sourcecode:: http

            Content-Type: application/json

            {
                "data": [
                    {
                        "id": "MQ==",
                        "name": "Plate XY",
                        "description": "Optional description",
                        "acquisitions": [
                            {
                                "id": "MQ==",
                                "name": "Acquisition XY",
                                "description": "",
                                "status": "UPLOADING" | "COMPLETE" | "WAITING"
                            },
                            ...
                        ],
                        "status": "UPLOADING" | "COMPLETE" | "WAITING"
                    },
                    ...
                ]
            }

        :statuscode 200: no error

    """
    logger.info('get all plates for experiment %d', experiment_id)
    with tm.utils.ExperimentSession(experiment_id) as session:
        plates = session.query(tm.Plate).all()
        return jsonify(data=plates)


@api.route('/experiments/<experiment_id>/plates/<plate_id>', methods=['DELETE'])
@jwt_required()
@decode_query_ids()
def delete_plate(experiment_id, plate_id):
    """
    .. http:delete:: /api/experiments/(string:experiment_id)/plates/(string:plate_id)

        Delete a specific plate.

        **Example response**:

        .. sourcecode:: http

            Content-Type: application/json

            {
                "message": "ok"
            }

        :statuscode 200: no error

    """
    logger.info('delete plate %d from experiment %d', plate_id, experiment_id)
    with tm.utils.ExperimentSession(experiment_id) as session:
        session.query(tm.Plate).filter_by(id=plate_id).delete()
    return jsonify(message='ok')


@api.route('/experiments/<experiment_id>/plates', methods=['POST'])
@jwt_required()
@assert_form_params('name')
@decode_query_ids()
def create_plate(experiment_id):
    """
    .. http:post:: /api/experiments/(string:experiment_id)/plates

        Create a new plate.

        **Example request**:

        .. sourcecode:: http

            Content-Type: application/json

            {
                "name": "Plate XY",
                "description": "Optional description"
            }

        **Example response**:

        .. sourcecode:: http

            Content-Type: application/json

            {
                "data": {
                    "id": "MQ==",
                    "name": "Plate XY",
                    "description": "Optional description",
                    "acquisitions": [],
                    "status": "WAITING"
                },
                "experiment_id": "MQ=="
            }

        :statuscode 200: no error

    """
    data = request.get_json()
    name = data.get('name')
    desc = data.get('description', '')

    logger.info('create plate "%s" for experiment %d', name, experiment_id)
    with tm.utils.ExperimentSession(experiment_id) as session:
        plate = tm.Plate(name=name, description=desc)
        session.add(plate)
        session.commit()

        return jsonify({
            'data': plate,
            'experiment_id': experiment_id
        })

@api.route('/experiments/<experiment_id>/plates/id', methods=['GET'])
@jwt_required()
@assert_query_params('plate_name')
@decode_query_ids()
def get_plate_id(experiment_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/plates/id

        Get the id of a plate given its name.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "id": "MQ=="
            }

        :query plate_name: the plates's name (required)
        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 404: no such experiment found

    """
    plate_name = request.args.get('plate_name')
    logger.info(
        'get ID of plate "%s" from experiment %d',
        plate_name, experiment_id
    )
    with tm.utils.ExperimentSession(experiment_id) as session:
        plate = session.query(tm.Plate).\
            filter_by(name=plate_name).\
            one()
        return jsonify({
            'id': encode_pk(plate.id)
        })


@api.route('/experiments/<experiment_id>/acquisitions', methods=['POST'])
@jwt_required()
@assert_form_params('plate_name', 'name')
@decode_query_ids()
@decode_form_ids()
def create_acquisition(experiment_id):
    """
    .. http:post:: /api/experiments/(string:experiment_id)/acquisitions

        Create an acquisition for a specified plate.

        **Example request**:

        .. sourcecode:: http

            Content-Type: application/json

            {
                "name": "Acquisition XY",
                "plate_name": "Plate XY"
            }

        **Example response**:

        .. sourcecode:: http

            Content-Type: application/json

            {
                "data": {
                    "id": "MQ==",
                    "name": "Plate XY",
                    "description": "Optional description"
                    "status": "WAITING"
                }
            }

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
            name=name, description=desc,
            plate_id=plate.id
        )
        session.add(acquisition)
        session.commit()
        return jsonify(data=acquisition)


@api.route(
    '/experiments/<experiment_id>/acquisitions/<acquisition_id>',
    methods=['DELETE']
)
@jwt_required()
@decode_query_ids()
def delete_acquisition(experiment_id, acquisition_id):
    """
    .. http:delete:: /api/experiments/(string:experiment_id)/acquisitions/(string:acquisition_id)

        Delete a specific acquisition.

        **Example response**:

        .. sourcecode:: http

            Content-Type: application/json

            {
                "message": "ok"
            }

        :statuscode 200: no error

    """
    logger.info(
        'delete acquisition %d from experiment %d',
        acquisition_id, experiment_id
    )
    with tm.utils.ExperimentSession(experiment_id) as session:
        session.query(tm.Acquisition).filter_by(id=acquisition_id).delete()
    return jsonify(message='ok')


@api.route(
    '/experiments/<experiment_id>/acquisitions/<acquisition_id>',
    methods=['GET']
)
@jwt_required()
@decode_query_ids()
def get_acquisition(experiment_id, acquisition_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/acquisitions/(string:acquisition_id)

        Get a specific acquisition object.

        **Example response**:

        .. sourcecode:: http

            Content-Type: application/json

            {
                "data":
                    {
                        "id": "MQ==",
                        "name": "Acquisition XY",
                        "description": "",
                        "status": "UPLOADING" | "COMPLETE" | "WAITING"
                    }
                }
            }

        :statuscode 200: no error
        :statuscode 404: no acquisition found with that id

    """
    logger.info(
        'get acquisition %d from experiment %d',
        acquisition_id, experiment_id
    )
    with tm.utils.ExperimentSession(experiment_id) as session:
        acquisition = session.query(tm.Acquisition).get(acquisition_id)
        return jsonify(data=acquisition)


@api.route('/experiments/<experiment_id>/acquisitions/id', methods=['GET'])
@jwt_required()
@assert_query_params('plate_name', 'acquisition_name')
@decode_query_ids()
def get_acquisition_id(experiment_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/plates/id

        Get the id of an acquistion given its name.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "id": "MQ=="
            }

        :query plate_name: the plates's name (required)
        :query acquisition_name: the acquistion's name (required)
        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 404: no such experiment found

    """
    plate_name = request.args.get('plate_name')
    acquisition_name = request.args.get('acquisition_name')
    logger.info(
        'get ID of acquistion "%s" for plate "%s" from experiment %d',
        acquisition_name, plate_name, experiment_id
    )
    with tm.utils.ExperimentSession(experiment_id) as session:
        acquisition = session.query(tm.Acquisition).\
            join(tm.Plate).\
            filter(
                tm.Plate.name == plate_name,
                tm.Acquisition.name == acquisition_name
            ).\
            one()
        return jsonify({
            'id': encode_pk(acquisition.id)
        })


@api.route(
    '/experiments/<experiment_id>/acquisitions/<acquisition_id>/image-files',
    methods=['GET']
)
@jwt_required()
@decode_query_ids()
def get_acquisition_image_files(experiment_id, acquisition_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/acquisitions/(string:acquisition_id)/image-files

        Get all files currently uploaded for the specified acquisition.

        **Example response**:

        .. sourcecode:: http

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
    '/experiments/<experiment_id>/acquisitions/<acquisition_id>/metadata-files',
    methods=['GET']
)
@jwt_required()
@decode_query_ids()
def get_acquisition_metadata_files(experiment_id, acquisition_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/acquisitions/(string:acquisition_id)/metadata-files

        Get all metadata files currently uploaded for the specified acquisition.

        **Example response**:

        .. sourcecode:: http

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

