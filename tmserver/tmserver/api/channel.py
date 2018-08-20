# TmServer - TissueMAPS server application.
# Copyright (C) 2016-2018 University of Zurich.
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
"""API view functions for querying :mod:`channel <tmlib.models.channel>`
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



@api.route('/experiments/<experiment_id>/channels', methods=['GET'])
@jwt_required()
@decode_query_ids('read')
def get_channels(experiment_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/channels

        Get channels for a specific experiment.

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
                                "image_size": {
                                    "width":  2200,
                                    "height": 2100
                                }
                            },
                            ...
                        ]
                    },
                    ...
                ]
            }

        :query name: name of a channel (optional)

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error

    """
    logger.info('get channels of experiment %d', experiment_id)
    name = request.args.get('name')
    with tm.utils.ExperimentSession(experiment_id) as session:
        channels = session.query(tm.Channel)
        if name is not None:
            logger.info('filter channels for name "%s"', name)
            channels = channels.filter_by(name=name)
        channels = channels.order_by(tm.Channel.name).all()
        return jsonify(data=channels)


@api.route(
    '/experiments/<experiment_id>/channels/<channel_id>', methods=['GET']
)
@jwt_required()
@decode_query_ids('read')
def get_channel(experiment_id, channel_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/channels/(string:channel_id)

        Get a channel.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": {
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
                }
            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 400: malformed request
        :statuscode 200: no error

    """
    data = request.get_json()
    name = data.get('name')
    logger.info('get channel %d of experiment %d', channel_id, experiment_id)
    with tm.utils.ExperimentSession(experiment_id) as session:
        channel = session.query(tm.Channel).get(channel_id)
    return jsonify(data=channel)


@api.route(
    '/experiments/<experiment_id>/channels/<channel_id>', methods=['PUT']
)
@jwt_required()
@decode_query_ids('read')
def update_channel(experiment_id, channel_id):
    """
    .. http:put:: /api/experiments/(string:experiment_id)/channels/(string:channel_id)

        Update a :class:`Channel <tmlib.models.channel.Channel>`.

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
    logger.info('rename channel %d of experiment %d', channel_id, experiment_id)
    with tm.utils.ExperimentSession(experiment_id) as session:
        channel = session.query(tm.Channel).get(channel_id)
        channel.name = name
    return jsonify(message='ok')


