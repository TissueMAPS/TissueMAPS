# TmServer - TissueMAPS server application.
# Copyright (C) 2016, 2018  University of Zurich
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
"""API view functions for querying :mod:`tools <tmlib.tools>` resources
as well as related :mod:`result <tmlib.models.result>` and
:mod:`plot <tmlib.models.plot>` resources.
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
from tmlib.workflow.utils import format_task_data

from tmserver.api import api
from tmserver.error import (
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
    data = request.get_json()
    payload = data.get('payload', {})
    session_uuid = data.get('session_uuid')
    tool_name = data.get('tool_name')
    logger.info('process request of tool "%s"', tool_name)

    manager = ToolRequestManager(
        experiment_id, tool_name, server_cfg.logging_verbosity
    )
    submission_id, user_name = manager.register_submission(current_identity.id)
    manager.store_payload(payload, submission_id)
    job = manager.create_job(submission_id, user_name)

    # with tm.utils.ExperimentSession(experiment_id) as session:
    #     session = session.get_or_create(ToolSession, uuid=session_uuid)
    #     session_id = session.id

    gc3pie.store_task(job)
    gc3pie.submit_task(job)

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
    .. http:get:: /api/experiments/(string:experiment_id)/tools/results/(string:tool_result_id)

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
    logger.info(
        'get tool result %d for experiment %d', tool_result_id, experiment_id
    )
    with tm.utils.ExperimentSession(experiment_id) as session:
        tool_result = session.query(tm.ToolResult).get(tool_result_id)
        if tool_result is None:
            raise ResourceNotFoundError(tm.ToolResult)
        return jsonify(data=tool_result)


@api.route(
    '/experiments/<experiment_id>/tools/results/<tool_result_id>',
    methods=['PUT']
)
@jwt_required()
@decode_query_ids('read')
def update_tool_result(experiment_id, tool_result_id):
    """
    .. http:put:: /api/experiments/(string:experiment_id)/tools/result/(string:tool_result_id)

        Update a :class:`ToolResult <tmlib.models.result.ToolResult>`.

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

        :statuscode 400: malformed request
        :statuscode 200: no error

    """
    data = request.get_json()
    name = data.get('name')
    logger.info(
        'rename tool result %d of experiment %d', tool_result_id, experiment_id
    )
    with tm.utils.ExperimentSession(experiment_id) as session:
        tool_result = session.query(tm.ToolResult).get(tool_result_id)
        tool_result.name = name
    return jsonify(message='ok')


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
                "data": [
                    {
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
                    },
                    ...
                ]
            }

        :query submission_id: ID of the corresponding submission (optional)
        :query name: name of the tool result (optional)

        :statuscode 400: malformed request
        :statuscode 200: no error

    """
    logger.info('get tool results')
    submission_id = request.args.get('submission_id', type=int)
    name = request.args.get('name')

    if submission_id is not None:
        logger.info(
            'filter tool results for submissions %d', submission_id
        )
        submission_ids = [submission_id]
    else:
        with tm.utils.MainSession() as session:
            logger.debug('filter tool results for current user')
            submissions = session.query(tm.Submission.id).\
                filter_by(user_id=current_identity.id, program='tool').\
                all()
            submission_ids = [s.id for s in submissions]
    with tm.utils.ExperimentSession(experiment_id) as session:
        tool_results = session.query(tm.ToolResult)
        if name is not None:
            logger.info('filter tool results for name "%s"', name)
            tool_results = tool_results.filter_by(name=name)
        tool_results = tool_results.\
            filter(tm.ToolResult.submission_id.in_(submission_ids)).\
            order_by(tm.ToolResult.submission_id).\
            distinct(tm.ToolResult.submission_id).\
            all()
        return jsonify(data=tool_results)


@api.route(
    '/experiments/<experiment_id>/tools/results/<tool_result_id>',
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
    '/experiments/<experiment_id>/tools/jobs', methods=['GET']
)
@jwt_required()
@decode_query_ids('read')
def get_tool_jobs(experiment_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/tools/jobs

        Get the status of each :class:`ToolJob <tmlib.models.jobs.ToolJob>`
        processing a tool request.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": [
                    {
                        "id": "dG1hcHM3NzYxOA==",
                        "name": "tool_Heatmap",
                        "submission_id": 4,
                        "submitted_at": "2017-04-01 10:42:10",
                        "state": "RUNNING",
                        "exitcode": null,
                        "memory": 1024,
                        "time": "1:21:33",
                        "cpu_time": "1:14:12"
                    },
                    ...
                ]
            }

        :query submission_id: numeric ID of the submission for which the job status should be retrieved (optional)
        :query tool_name: name of a tool for which job status should be retrieved (optional)
        :query state: state jobs should have, e.g. RUNNING (optional)
        :statuscode 400: malformed request
        :statuscode 200: no error

    """
    logger.info('get status of tool jobs for experiment %d', experiment_id)
    submission_id = request.args.get('submission_id', type=int)
    tool_name = request.args.get('tool_name')
    state = request.args.get('state')

    # TODO: batch_size, index - see workflow.get_jobs_status()
    with tm.utils.MainSession() as session:
        tool_jobs = session.query(
                tm.Task.created_at, tm.Task.updated_at,
                tm.Task.id, tm.Task.name, tm.Task.type, tm.Task.time,
                tm.Task.cpu_time, tm.Task.memory,
                tm.Task.state, tm.Task.submission_id, tm.Task.exitcode
            ).\
            join(tm.Submission, tm.Task.submission_id == tm.Submission.id).\
            filter(
                tm.Submission.program == 'tool',
                tm.Submission.experiment_id == experiment_id,
                tm.Submission.user_id == current_identity.id
            )
        if state is not None:
            logger.info('filter tool jobs for state "%s"', state)
            tool_jobs = tool_jobs.filter(tm.Task.state == state)
        if tool_name is not None:
            logger.info('filter tool jobs for tool name "%s"', tool_name)
            tool_jobs = tool_jobs.filter(tm.Task.name == 'tool_%s' % tool_name)
        if submission_id is not None:
            logger.info('filter tool jobs for submission %d', submission_id)
            tool_jobs = tool_jobs.\
                filter(tm.Task.submission_id == submission_id)
        tool_jobs = tool_jobs.all()
        tool_job_status = list()
        for j in tool_jobs:
            status = format_task_data(
                j.name, j.type, j.created_at, j.updated_at, j.state, j.exitcode,
                j.memory, j.time, j.cpu_time
            )
            status['id'] = encode_pk(j.id)
            status['submission_id'] = j.submission_id
            status['submitted_at'] = str(j.created_at)
            tool_job_status.append(status)
        return jsonify(data=tool_job_status)


@api.route(
    '/experiments/<experiment_id>/tools/jobs/<job_id>/log',
    methods=['GET']
)
@jwt_required()
@decode_query_ids('read')
def get_tool_job_log(experiment_id, job_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/tools/jobs/(string:job_id)/log

        Get the log output of a :class:`ToolJob <tmlib.tools.jobs.ToolJob>`
        for a given :class:`ToolResult <tmlib.models.result.ToolResult>`.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": {
                    "stdout": "bla bla bla",
                    "stderr": ""
                }
            }

        :statuscode 400: malformed request
        :statuscode 200: no error

    """
    logger.info(
        'get log of tool job %d for experiment %d',
        job_id, experiment_id
    )
    job = gc3pie.retrieve_task(job_id)
    stdout_file = os.path.join(job.output_dir, job.stdout)
    with open(stdout_file, 'r') as f:
        out = f.read()
    stderr_file = os.path.join(job.output_dir, job.stderr)
    with open(stderr_file, 'r') as f:
        err = f.read()
    return jsonify(data={'stdout': out, 'stderr': err})
