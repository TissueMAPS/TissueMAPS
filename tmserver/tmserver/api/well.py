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
"""API view functions for querying :mod:`well <tmlib.models.well>`
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


@api.route('/experiments/<experiment_id>/wells', methods=['GET'])
@jwt_required()
@decode_query_ids('read')
def get_wells(experiment_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/wells

        Get wells for the specified experiments.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": [
                    {
                        "id": "MQ==",
                        "name": "D04",
                        "description": ""
                    },
                    ...
                ]

            }

        :query plate_name: name of a plate (optional)
        :query name: name of a well (optional)

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 404: no matching cycle found

    """
    logger.info('get wells for experiment %d', experiment_id)
    plate_name = request.args.get('plate_name')
    name = request.args.get('name')
    with tm.utils.ExperimentSession(experiment_id) as session:
        wells = session.query(tm.Well)
        if name is not None:
            wells = wells.filter_by(name=name)
        if plate_name is not None:
            wells = wells.\
                join(tm.Plate).\
                filter(tm.Plate.name == plate_name)
        wells = wells.order_by(tm.Well.name).all()
        return jsonify(data=wells)


@api.route('/experiments/<experiment_id>/wells/<well_id>', methods=['GET'])
@jwt_required()
@decode_query_ids('read')
def get_well(experiment_id, well_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/wells/(string:well_id)

        Get a :class:`Well <tmlib.models.well.Well>`.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": {
                    "id": "MQ==",
                    "name": "D04",
                    "description": ""
                }

            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 404: no matching cycle found

    """
    logger.info('get well %d for experiment %d', well_id, experiment_id)
    with tm.utils.ExperimentSession(experiment_id) as session:
        well = session.query(tm.Well).get(well_id)
        return jsonify(data=well)


@api.route('/experiments/<experiment_id>/wells/<well_id>', methods=['PUT'])
@jwt_required()
@assert_form_params('description')
@decode_query_ids('write')
def update_well_description(experiment_id, well_id):
    """
    .. http:put:: /api/experiments/(string:experiment_id)/wells/(string:well_id)

        Update description of a :class:`Well <tmlib.models.well.Well>`.

        **Example request**:

        .. sourcecode:: http

            Content-Type: application/json

            {
                "description": {}
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
    description = data.get('description')
    logger.info(
        'update description of well %d of experiment %d', well_id, experiment_id
    )
    with tm.utils.ExperimentSession(experiment_id) as session:
        well = session.query(tm.Well).get(well_id)
        well.description = description
    return jsonify(message='ok')

