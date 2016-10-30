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
"""API view functions that deal with data analysis tools and their results"""
import os
import json
import logging
from flask import jsonify, request, current_app
from flask_jwt import jwt_required
from flask_jwt import current_identity

import tmlib.models as tm
from tmlib.writers import JsonWriter

from tmserver.api import api
from tmserver.error import (
    MalformedRequestError,
    ResourceNotFoundError,
    NotAuthorizedError
)
from tmserver.util import decode_query_ids, decode_form_ids
from tmserver.util import assert_query_params, assert_form_params
from tmserver.tool.job import ToolJob
from tmserver.extensions import gc3pie

from tmtoolbox.result import ToolResult, LabelLayer
from tmtoolbox import SUPPORTED_TOOLS
from tmtoolbox import get_tool_class


logger = logging.getLogger(__name__)


def _create_mapobject_feature(mapobject_id, geometry_description):
    """Creates a GeoJSON feature for the given mapobject and GeoJSON geometry.

    Parameters
    ----------
    mapobject_id: int
        ID of the mapobject
    geometry_description: XXX
        description of a GeoJSON geometry

    Returns
    -------
    dict
    """
    return {
        'type': 'Feature',
        'geometry': geometry_description,
        'properties': {
            'id': str(mapobject_id)
        }
    }


@api.route('/tools', methods=['GET'])
@jwt_required()
def get_tools():
    """
    .. http:get:: /api/tools

        Get a list of supported tools.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": [
                    {
                        "name": "Cluster Tool",
                        "icon": "<span>CLU</span>",
                        "description",
                        "methods": [...]
                    },
                    ...
                ]
            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error

    """
    tool_descriptions = list()
    for name in SUPPORTED_TOOLS:
        tool_cls = get_tool_class(name)
        tool_descriptions.append({
            'name': tool_cls.__name__,
            'icon': tool_cls.__icon__,
            'description': tool_cls.__description__,
            'methods': getattr(tool_cls, '__methods__', [])
        })
    return jsonify(data=tool_descriptions)


@api.route(
    '/experiments/<experiment_id>/tools/request', methods=['POST']
)
@jwt_required()
@decode_query_ids()
@assert_form_params('payload', 'session_uuid', 'tool_name')
def process_tool_request(experiment_id):
    """
    .. http:post:: /api/experiments/(string:experiment_id)/tools/request

        Processes a generic tool request sent by the client.

        **Example request**:

        .. sourcecode:: http

            Content-Type: application/json

            {
                "tool_name": "Cluster Tool",
                "payload": any object,
                "session_uuid": string
            }

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "message": "ok"
            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error

    """
    data = request.get_json()
    payload = data.get('payload', {})
    session_uuid = data.get('session_uuid')
    tool_name = data.get('tool_name')

    # Instantiate the correct tool plugin class.
    logger.info('process request of tool "%s"', tool_name)

    with tm.utils.MainSession() as session:
        experiment = session.query(tm.ExperimentReference).get(experiment_id)
        user_name = experiment.user.name
        tool_dir = os.path.join(experiment.tools_location, tool_name)
        submission = tm.Submission(experiment_id, program='tool')
        session.add(submission)
        session.flush()
        submission_id = submission.id

    tool_log_dir = os.path.join(tool_dir, 'logs')
    tool_batch_dir = os.path.join(tool_dir, 'batches')
    if not os.path.exists(tool_log_dir):
        os.makedirs(tool_log_dir)
    if not os.path.exists(tool_batch_dir):
        os.makedirs(tool_batch_dir)

    with tm.utils.ExperimentSession(experiment_id) as session:
        session = session.get_or_create(ToolSession, uuid=session_uuid)
        session_id = session.id

    batch_filename = '%s_%d.json' % (tool_name, session_id)
    batch_location = os.path.join(tool_batch_dir, batch_filename)
    with JsonWriter(batch_location) as f:
        f.write(payload)

    # Create and submit tool job for asynchronous processing on the cluster
    if cfg.use_spark:
        args = ['spark-submit', '--master', cfg.spark_master]
        if cfg.spark_master == 'yarn':
            args.extend(['--deploy-mode', 'client'])
        # TODO: ship Python dependencies
        # args.extend([
        #     '--py-files', cfg.spark_tmtoolbox_egg
        # ])
    else:
        args = []
    args.extend([
        'tmtool', str(experiment_id),
        '--tool', tool_name,
        '--submission_id', str(submission_id),
        '--batch_file', batch_location,
    ])
    if cfg.use_spark:
        args.append('--use_spark')

    job = ToolJob(
        tool_name=tool_name,
        arguments=args,
        output_dir=tool_log_dir,
        submission_id=submission_id,
        user_name=user_name
    )
    gc3pie.store_jobs(job)
    gc3pie.submit_jobs(job)

    return jsonify(message='ok')


@api.route(
    '/experiments/<experiment_id>/tools/result', methods=['GET']
)
@decode_query_ids()
@assert_query_params('submission_id')
def get_tool_result(experiment_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/tools/result

        Get the result of a previous tool request including a label layer that
        can be queried for tiled cell labels as well as optional plots.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": {
                    "id": "MQ==",
                    "name": "Cluster Result 1",
                    "submission_id": 1,
                    "layer": {
                        "id": "MQ==",
                        "type": "HeatmapLayer",
                        "attributes": {
                            "min": 0,
                            "max": 2414
                        }
                    },
                    "plots": []
                }
            }

        :statuscode 400: malformed request
        :statuscode 200: no error

    """
    submission_id = request.args.get('submission_id', type=int)
    logger.info('get tool result for submission %d', submission_id)
    with tm.utils.ExperimentSession(experiment_id) as session:
        tool_result = session.query(ToolResult).\
            filter_by(submission_id=submission_id).\
            one()
        return jsonify(data=tool_result)


@api.route(
    '/experiments/<experiment_id>/tools/status', methods=['GET']
)
@decode_query_ids()
def get_tool_job_status(experiment_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/tools/status

        Get the status of a job processing a tool request.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": [
                    {
                        "state": string,
                        "submission_id": number,
                        "exitcode": number
                    },
                    ...
                ]
            }

        :statuscode 400: malformed request
        :statuscode 200: no error

    """
    logger.info('get status of tool jobs for experiment %d', experiment_id)
    with tm.utils.MainSession() as session:
        tool_job_status_ = session.query(
                tm.Task.state, tm.Task.submission_id, tm.Task.exitcode
            ).\
            join(tm.Submission).\
            filter(
                tm.Submission.program == 'tool',
                tm.Submission.experiment_id == experiment_id
            ).\
            all()
        tool_job_status = \
            [{'state': st[0], 'submission_id': st[1], 'exitcode': st[2]}
             for st in tool_job_status_]

        return jsonify(data=tool_job_status)


@api.route(
    '/experiments/<experiment_id>/labellayers/<label_layer_id>/tiles',
    methods=['GET']
)
@decode_query_ids()
@assert_query_params('x', 'y', 'z', 'zplane', 'tpoint')
def get_label_layer_tiles(experiment_id, label_layer_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/labellayers/(string:label_layer_id)/tiles

        Get all mapobjects together with the labels that were assigned to them
        for a given tool result and tile coordinate.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "type": "FeatureCollection",
                "features": [
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [x1, y1], [x2, y2], ...
                        ]]
                    },
                    "properties": {
                        "label": 123
                        "id": id
                    }
                    ...
                ]
            }

        :query x: zero-based `x` coordinate
        :query y: zero-based `y` coordinate
        :query z: zero-based zoom level index
        :query zplane: the zplane of the associated layer
        :query tpoint: the time point of the associated layer

        :statuscode 400: malformed request
        :statuscode 200: no error

    """
    # The coordinates of the requested tile
    x = request.args.get('x', type=int)
    y = request.args.get('y', type=int)
    z = request.args.get('z', type=int)
    zplane = request.args.get('zplane', type=int)
    tpoint = request.args.get('tpoint', type=int)

    with tm.utils.ExperimentSession(experiment_id) as session:
        label_layer = session.query(LabelLayer).get(label_layer_id)
        logger.info('get result tiles for label layer "%s"', label_layer.type)
        mapobject_type = session.query(tm.MapobjectType).\
            get(label_layer.mapobject_type_id)
        query_res = mapobject_type.get_mapobject_outlines_within_tile(
            x, y, z, zplane=zplane, tpoint=tpoint
        )

        features = []
        has_mapobjects_within_tile = len(query_res) > 0

        if has_mapobjects_within_tile:
            mapobject_ids = [c[0] for c in query_res]
            mapobject_id_to_label = label_layer.get_labels(mapobject_ids)

            features = [
                {
                    'type': 'Feature',
                    'geometry': json.loads(geom_geojson_str),
                    'properties': {
                        'label': mapobject_id_to_label[id],
                        'id': id
                     }
                }
                for id, geom_geojson_str in query_res
            ]

        return jsonify({
            'type': 'FeatureCollection',
            'features': features
        })

