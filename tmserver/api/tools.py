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
"""User interface view functions that deal with data analysis tools and their
results.
"""
import os
import json
import logging
from flask import jsonify, request, current_app
from flask_jwt import jwt_required, current_identity
from sqlalchemy import distinct

import tmlib.models as tm
from tmlib import cfg as tmlib_cfg
from tmlib.writers import JsonWriter
from tmlib.tools.jobs import ToolJob
from tmlib.log import LEVELS_TO_VERBOSITY
from tmlib.tools import get_available_tools, get_tool_class
from tmlib.tools.manager import ToolRequestManager

from tmserver.api import api
from tmserver.error import (
    MalformedRequestError,
    ResourceNotFoundError,
    NotAuthorizedError
)
from tmserver.util import decode_query_ids, decode_form_ids
from tmserver.util import assert_query_params, assert_form_params
from tmserver.model import encode_pk
from tmserver.extensions import gc3pie
from tmserver import cfg as server_cfg


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
    logger.info('get available tools')
    tool_descriptions = list()
    available_tools = get_available_tools()
    for name in available_tools:
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
@decode_query_ids('read')
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
                "data": {
                    "submission_id": "MQ=="
                }
            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error

    """
    logger.info('process request of tool "%s"', tool_name)
    data = request.get_json()
    payload = data.get('payload', {})
    session_uuid = data.get('session_uuid')
    tool_name = data.get('tool_name')

    verbosity = LEVELS_TO_VERBOSITY[server_cfg.log_level]
    manager = ToolRequestManager(experiment_id, tool_name, verbosity)
    submission_id, user_name = manager.register_submission(current_identity.id)
    manager.write_batch_file(payload, submission_id)
    job = manager.create_job(submission_id, user_name)

    # with tm.utils.ExperimentSession(experiment_id) as session:
    #     session = session.get_or_create(ToolSession, uuid=session_uuid)
    #     session_id = session.id

    gc3pie.store_jobs(job)
    gc3pie.submit_jobs(job)

    return jsonify(data={
        'submission_id': submission_id
    })


@api.route(
    '/experiments/<experiment_id>/tools/results/<tool_result_id>',
    methods=['GET']
)
@jwt_required()
@decode_query_ids('read')
def get_tool_result(experiment_id, tool_result_id):
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
                    "submission_id": 117,
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
        tool_result = session.query(tm.ToolResult).get(tool_result_id)
        if tool_result is None:
            raise ResourceNotFoundError(tm.ToolResult)
        return jsonify(data=tool_result)

@api.route(
    '/experiments/<experiment_id>/tools/results', methods=['GET']
)
@jwt_required()
@decode_query_ids('read')
def get_tool_results(experiment_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/tools/result

        Get the result of a previous tool request including a label layer that
        can be queried for tiled cell labels as well as optional plots.

        **Example request**:

        .. sourcecode:: http

            Content-Type: application/json

            {
                "submission_id": 117
            }

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": {
                    "id": "MQ==",
                    "name": "Cluster Result 1",
                    "submission_id": 117,
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

        :query submission_id: ID of the corresponding submission (optional)

        :statuscode 400: malformed request
        :statuscode 200: no error

    """
    submission_id = request.args.get('submission_id', None)
    logger.info('get tool results')

    if submission_id is not None:
        logging.info(
            'filter tool results for submissions %d', int(submission_id)
        )
        submission_ids = [int(submission_id)]
    else:
        with tm.utils.MainSession() as session:
            logger.debug('filter tool results for current user')
            submissions = session.query(tm.Submission.id).\
                filter_by(user_id=current_identity.id, program='tool').\
                all()
            submission_ids = [s.id for s in submissions]
    with tm.utils.ExperimentSession(experiment_id) as session:
        tool_results = session.query(tm.ToolResult).\
            filter(tm.ToolResult.submission_id.in_(submission_ids)).\
            order_by(tm.ToolResult.submission_id).\
            distinct(tm.ToolResult.submission_id).\
            all()
        return jsonify(data=tool_results)


@api.route(
    '/experiments/<experiment_id>/tools/result/<tool_result_id>',
    methods=['DELETE']
)
@jwt_required()
@decode_query_ids('read')
def delete_tool_result(experiment_id, tool_result_id):
    """
    .. http:delete:: /api/experiments/(string:experiment_id)/tools/result/(string:tool_result_id)

        Delete a tool result.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "message": "ok"
            }


        :statuscode 200: no error

    """
    logger.info('delete tool result %d', tool_result_id)
    with tm.utils.ExperimentSession(experiment_id) as session:
        session.query(tm.ToolResult).\
            filter_by(id=tool_result_id).\
            delete()
    return jsonify(message='ok')


@api.route(
    '/experiments/<experiment_id>/tools/status', methods=['GET']
)
@jwt_required()
@decode_query_ids('read')
def get_tool_job_status(experiment_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/tools/status

        Get the status of one or multiple jobs processing a tool request.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            If no submission_id was supplied:

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

            If a submission_id was supplied:

            {
                "data": {
                    "state": string,
                    "submission_id": number,
                    "exitcode": number
                }
            }

        :query submission_id: numeric id of the submission for which the job status should be retrieved (optional).
        :statuscode 400: malformed request
        :statuscode 200: no error

    """
    submission_id = request.args.get('submission_id', type=int)

    if submission_id is None:
        logger.info('get status of tool jobs for experiment %d', experiment_id)
    else:
        logger.info('get status of single tool job %d', submission_id)

    with tm.utils.MainSession() as session:
        query = session.query(
                tm.Task.state, tm.Task.submission_id, tm.Task.exitcode
            ).\
            join(tm.Submission)
        if submission_id is None:
            tool_jobs = query.\
            filter(
                tm.Submission.program == 'tool',
                tm.Submission.experiment_id == experiment_id,
                tm.Submission.user_id == current_identity.id
            ).\
            all()
            tool_job_status = [
                {
                    'state': j.state,
                    'submission_id': j.submission_id,
                    'exitcode': j.exitcode
                }
                for j in tool_jobs
            ]
            return jsonify(data=tool_job_status)
        else:
            tool_job = query.\
            filter(
                tm.Submission.program == 'tool',
                tm.Submission.experiment_id == experiment_id,
                tm.Submission.id == submission_id,
                tm.Submission.user_id == current_identity.id
            ).\
            one()
            tool_job_status = {
                'state': tool_job.state,
                'submission_id': tool_job.submission_id,
                'exitcode': tool_job.exitcode
            }
            return jsonify(data=tool_job_status)
