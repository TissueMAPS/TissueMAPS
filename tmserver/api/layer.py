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
"""API view functions for querying :mod:`layer <tmlib.models.layer>`
and :mod:`tile <tmlib.models.tile>` resources.
"""
import json
import logging
from flask import jsonify, request, send_file
from flask_jwt import jwt_required

import tmlib.models as tm

from tmserver.api import api
from tmserver.util import (
    decode_query_ids, decode_form_ids, assert_query_params, assert_form_params
)

logger = logging.getLogger(__name__)


@api.route('/experiments/<experiment_id>/channel_layers', methods=['GET'])
@jwt_required()
@decode_query_ids('read')
def get_channel_layers(experiment_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/channel_layers

        Get channel layers.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": [
                    {
                        "id": "MQ==",
                        "max_zoom": 12,
                        "tpoint": 0,
                        "zplane": 0,
                        "max_intensity": 6056,
                        "min_intensity": 0,
                        "experiment_id": "MQ==",
                        "image_size": {
                            "width":  2200,
                            "height": 2100
                        }
                    },
                    ...
                ]
            }

        :query channel_name: the name of the channel (optional)
        :query tpoint: the time point associated with this layer (optional)
        :query zplane: the zplane of this layer (optional)

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 404: no matching layer found

    """
    logger.info('get channel layers of experiment %d', experiment_id)
    channel_name = request.args.get('channel_name')
    tpoint = request.args.get('tpoint', type=int)
    zplane = request.args.get('zplane', type=int)
    with tm.utils.ExperimentSession(experiment_id) as session:
        layers = session.query(tm.ChannelLayer)
        if tpoint is not None:
            logger.info('filter channel layers for tpoint %d', tpoint)
            layers = layers.filter_by(tpoint=tpoint)
        if zplane is not None:
            logger.info('filter channel layers for zplane %d', zplane)
            layers = layers.filter_by(zplane=zplane)
        if channel_name is not None:
            logger.info(
                'filter channel layers for channel with name "%s"', channel_name
            )
            layers = layers.\
                join(tm.Channel).\
                filter(tm.Channel.name == channel_name)
        layers = layers.all()
        return jsonify(data=layers)


@api.route('/experiments/<experiment_id>/segmentation_layers', methods=['GET'])
@jwt_required()
@decode_query_ids('read')
def get_segmentation_layers(experiment_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/segmentation_layers

        Get segmentation layers.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": [
                    {
                        "id": "MQ==",
                        "tpoint": 0,
                        "zplane": 0,
                        "image_size": {
                            "width":  2200,
                            "height": 2100
                        }
                    },
                    ...
                ]
            }

        :query mapobject_type_name: the name of the mapobject type (optional)
        :query tpoint: the time point associated with this layer (optional)
        :query zplane: the zplane of this layer (optional)

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 404: no matching layer found

    """
    logger.info('get segmentation layers of experiment %d', experiment_id)
    mapobject_type_name = request.args.get('mapobject_type_name')
    tpoint = request.args.get('tpoint', type=int)
    zplane = request.args.get('zplane', type=int)
    with tm.utils.ExperimentSession(experiment_id) as session:
        layers = session.query(tm.SegmentationLayer)
        if tpoint is not None:
            logger.info('filter segmentation layers for tpoint %d', tpoint)
            layers = layers.filter_by(tpoint=tpoint)
        if zplane is not None:
            logger.info('filter segmentation layers for zplane %d', zplane)
            layers = layers.filter_by(zplane=zplane)
        if channel_name is not None:
            logger.info(
                'filter segmentation layers for mapobject type with name "%s"',
                channel_name
            )
            layers = layers.\
                join(tm.MapobjectType).\
                filter(tm.MapobjectType.name == mapobject_type_name)
        layers = layers.all()
        return jsonify(data=layers)

