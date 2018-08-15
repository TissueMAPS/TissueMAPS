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
"""API view functions for querying :mod:`plate <tmlib.models.plate>`
resources.
"""
import json
import logging
from flask import jsonify, send_file, request
from flask_jwt import jwt_required

import tmlib.models as tm

from tmserver.util import (
    decode_query_ids, decode_form_ids, is_true, is_false,
    assert_query_params, assert_form_params
)
from tmserver.api import api
from tmserver.error import *


logger = logging.getLogger(__name__)


@api.route('/experiments/<experiment_id>/plates/<plate_id>', methods=['GET'])
@jwt_required()
@decode_query_ids('read')
def get_plate(experiment_id, plate_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/plates/(string:plate_id)

        Get a plate given its id and the it of its parent experiment.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
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

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 404: no such plate or experiment

    """
    logger.info('get plate %d from experiment %d', plate_id, experiment_id)
    with tm.utils.ExperimentSession(experiment_id) as session:
        plate = session.query(tm.Plate).get(plate_id)
        return jsonify(data=plate)

@api.route(
    '/experiments/<experiment_id>/plates/<plate_id>', methods=['PUT']
)
@jwt_required()
@assert_form_params('name')
@decode_query_ids('read')
def update_plate(experiment_id, plate_id):
    """
    .. http:put:: /api/experiments/(string:experiment_id)/plates/(string:plate_id)

        Update a :class:`Plate <tmlib.models.plate.Plate>`.

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
    logger.info('rename plate %d of experiment %d', plate_id, experiment_id)
    with tm.utils.ExperimentSession(experiment_id) as session:
        plate = session.query(tm.Plate).get(plate_id)
        plate.name = name
    return jsonify(message='ok')


@api.route('/experiments/<experiment_id>/plates', methods=['GET'])
@jwt_required()
@decode_query_ids('read')
def get_plates(experiment_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/plates

        Get plates for the specified experiment.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
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

        :query name: name of a plate (optional)

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error

    """
    plate_name = request.args.get('name')
    logger.info('get plates for experiment %d', experiment_id)
    with tm.utils.ExperimentSession(experiment_id) as session:
        plates = session.query(tm.Plate)
        if plate_name is not None:
            logger.info('filter plates for name: %s', name)
            plates = plates.filter_by(name=plate_name)
        return jsonify(data=plates.all())


@api.route('/experiments/<experiment_id>/plates/<plate_id>', methods=['DELETE'])
@jwt_required()
@decode_query_ids('write')
def delete_plate(experiment_id, plate_id):
    """
    .. http:delete:: /api/experiments/(string:experiment_id)/plates/(string:plate_id)

        Delete a specific :class:`Plate <tmlib.models.plate.Plate>`.

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
    logger.info('delete plate %d from experiment %d', plate_id, experiment_id)
    with tm.utils.ExperimentSession(experiment_id) as session:
        session.query(tm.Plate).filter_by(id=plate_id).delete()
        # TODO: DELETE CASCADE mapobjects, channel_layer_tiles
    return jsonify(message='ok')


@api.route('/experiments/<experiment_id>/plates', methods=['POST'])
@jwt_required()
@assert_form_params('name')
@decode_query_ids('write')
def create_plate(experiment_id):
    """
    .. http:post:: /api/experiments/(string:experiment_id)/plates

        Create a new :class:`Plate <tmlib.models.plate.Plate>`.

        **Example request**:

        .. sourcecode:: http

            Content-Type: application/json

            {
                "name": "Plate XY",
                "description": "Optional description"
            }

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": {
                    "id": "MQ==",
                    "name": "Plate XY",
                    "description": "Optional description",
                    "acquisitions": [],
                    "status": "WAITING"
                }
            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error

    """
    data = request.get_json()
    name = data.get('name')
    desc = data.get('description', '')

    logger.info('create plate "%s" for experiment %d', name, experiment_id)
    with tm.utils.ExperimentSession(experiment_id) as session:
        plate = tm.Plate(
            name=name, experiment_id=experiment_id, description=desc
        )
        session.add(plate)
        session.commit()
        return jsonify(data=plate)


