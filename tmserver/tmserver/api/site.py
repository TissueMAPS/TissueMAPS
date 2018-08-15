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
"""API view functions for querying :mod:`site <tmlib.models.site>` resources.
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


@api.route('/experiments/<experiment_id>/sites', methods=['GET'])
@jwt_required()
@decode_query_ids('read')
def get_sites(experiment_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/sites

        Get sites.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": [
                    {
                        "id": "MQ==",
                        "y": 0,
                        "x": 1,
                        "height": 2230,
                        "width": 2140
                    },
                    ...
                ]

            }

        :query plate_name: name of a plate (optional)
        :query well_name: name of a well (optional)
        :query well_pox_y: y-coordinate of a site relative to its well (optional)
        :query well_pox_x: x-coordinate of a site relative to its well (optional)

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 404: no matching cycle found

    """
    logger.info('get sites for experiment %d', experiment_id)
    plate_name = request.args.get('plate_name')
    well_name = request.args.get('well_name')
    well_pos_y = request.args.get('well_pos_y', type=int)
    well_pos_x = request.args.get('well_pos_x', type=int)
    with tm.utils.ExperimentSession(experiment_id) as session:
        sites = session.query(tm.Site).\
            join(tm.Well).\
            join(tm.Plate)
        if well_name is not None:
            sites = sites.filter(tm.Well.name == well_name)
        if plate_name is not None:
            sites = sites.filter(tm.Plate.name == plate_name)
        if well_pos_y is not None:
            sites = sites.filter(tm.Site.y == well_pos_y)
        if well_pos_x is not None:
            sites = sites.filter(tm.Site.x == well_pos_x)
        sites = sites.order_by(
                tm.Plate.name, tm.Well.name, tm.Site.y, tm.Site.x
            )\
            .all()
        return jsonify(data=sites)


@api.route('/experiments/<experiment_id>/sites/<site_id>', methods=['GET'])
@jwt_required()
@decode_query_ids('read')
def get_site(experiment_id, site_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/sites/(string:site_id)

        Get a :class:`Site <tmlib.models.site.Site>`.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": {
                    "id": "MQ==",
                    "y": 0,
                    "x": 1,
                    "height": 2230,
                    "width": 2140
                }

            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 404: no matching cycle found

    """
    logger.info('get site %d for experiment %d', site_id, experiment_id)
    with tm.utils.ExperimentSession(experiment_id) as session:
        site = session.query(tm.Site).get(site_id)
        return jsonify(data=site)

