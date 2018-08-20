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
"""API view functions for querying :mod:`cycle <tmlib.models.cycle>`
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


@api.route('/experiments/<experiment_id>/cycles', methods=['GET'])
@jwt_required()
@decode_query_ids('read')
def get_cycles(experiment_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/cycles

        Get cycles for the specified experiments.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": [
                    {
                        "id": "MQ==",
                        "index": 0,
                        "tpoint": 0
                    },
                    ...
                ]
            }

        :query plate_name: the name of the plate (optional)
        :query index: the cycle's index (optional)

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 404: no matching cycle found

    """
    logger.info('get cycles for experiment %d', experiment_id)
    plate_name = request.args.get('plate_name')
    cycle_index = request.args.get('index', type=int)
    with tm.utils.ExperimentSession(experiment_id) as session:
        cycles = session.query(tm.Cycle.id)
        if plate_name is not None:
            cycles = cycles.\
                join(tm.Plate).\
                filter(tm.Plate.name == plate_name)
        if cycle_index is not None:
            cycles = cycles.filter(tm.Cycle.index == cycle_index)
        cycles = cycles.order_by(tm.Cycle.index).all()
        return jsonify(data=cycles)


@api.route('/experiments/<experiment_id>/cycles/<cycle_id>', methods=['GET'])
@jwt_required()
@decode_query_ids('read')
def get_cycle(experiment_id, cycle_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/cycles/(string:cycle_id)

        Get a cycle.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": {
                    "id": "MQ==",
                    "index": 0,
                    "tpoint": 0
                }
            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 404: no matching cycle found

    """
    logger.info('get cycle %d for experiment %d', cycle_id, experiment_id)
    with tm.utils.ExperimentSession(experiment_id) as session:
        cycle = session.query(tm.Cycle).get(cycle_id)
        return jsonify(data=cycle)

