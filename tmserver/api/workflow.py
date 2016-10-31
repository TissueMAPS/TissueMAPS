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
"""API view functions for workflow management."""
import json
import os
from cStringIO import StringIO
import logging
import numpy as np
from flask import jsonify, send_file, current_app, request
from flask_jwt import jwt_required
from flask_jwt import current_identity

import tmlib.models as tm
from tmlib.workflow.description import WorkflowDescription
from tmlib.workflow.submission import SubmissionManager
from tmlib.workflow.workflow import Workflow
from tmlib.logging_utils import LEVELS_TO_VERBOSITY
from tmlib import cfg as lib_cfg

from tmserver.util import decode_query_ids, decode_form_ids
from tmserver.util import assert_query_params, assert_form_params
from tmserver.model import decode_pk
from tmserver.model import encode_pk
from tmserver.extensions import gc3pie
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




@api.route('/experiments/<experiment_id>/workflow/submit', methods=['POST'])
@jwt_required()
@assert_form_params('description')
@decode_query_ids()
def submit_workflow(experiment_id):
    """
    .. http:post:: /api/experiments/(string:experiment_id)/workflow/submit

        Submit a workflow based on a ``WorkflowDescription``.
        Please refer to the respective class documention for more details on how to
        structure such a description object.

        **Example request**:

            Content-Type: application/json

            {
                "description": {...}
            }

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "message": "ok",
                "submission_id": 1
            }

        :statuscode 200: no error

    """
    logger.info('submit workflow for experiment %d', experiment_id)
    data = request.get_json()
    # data = json.loads(request.data)
    workflow_description = WorkflowDescription(**data['description'])
    with tm.utils.MainSession() as session:
        experiment = session.query(tm.ExperimentReference).get(experiment_id)
        experiment.persist_workflow_description(workflow_description)
    submission_manager = SubmissionManager(experiment_id, 'workflow')
    submission_id, user_name = submission_manager.register_submission()
    verbosity = LEVELS_TO_VERBOSITY[server_cfg.log_level]
    workflow = Workflow(
        experiment_id=experiment_id,
        verbosity=verbosity,
        submission_id=submission_id,
        user_name=user_name,
        description=workflow_description
    )
    gc3pie.store_jobs(workflow)
    gc3pie.submit_jobs(workflow)

    return jsonify({
        'message': 'ok',
        'submission_id': workflow.submission_id
    })


@api.route('/experiments/<experiment_id>/workflow/resubmit', methods=['POST'])
@jwt_required()
@assert_form_params('description')
@decode_query_ids()
def resubmit_workflow(experiment_id):
    """
    .. http:post:: /api/experiments/(string:experiment_id)/workflow/resubmit

        Resubmit a workflow for an experiment providing a new ``WorkflowDescription``.
        Please refer to the respective class documention for more details on how to
        structure such a description object.

        **Example request**:

            Content-Type: application/json

            {
                "description": {...}
            }

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "message": "ok",
                "submission_id": 1
            }

        :statuscode 200: no error

    """
    logger.info('resubmit workflow for experiment %d', experiment_id)
    data = json.loads(request.data)
    index = data.get('index', 0)
    workflow_description = WorkflowDescription(**data['description'])
    workflow = gc3pie.retrieve_jobs(experiment_id, 'workflow')
    workflow.update_description(workflow_description)
    workflow.update_stage(index)
    gc3pie.resubmit_jobs(workflow, index)
    return jsonify({
        'message': 'ok',
        'submission_id': workflow.submission_id
    })


@api.route(
    '/experiments/<experiment_id>/workflow/status', methods=['GET']
)
@jwt_required()
@decode_query_ids()
def get_workflow_status(experiment_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/workflow/status

        Query the status for the currently running workflow for the specified experiment.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": status # TODO
            }

        :statuscode 200: no error

    """
    logger.info('get workflow status for experiment %d', experiment_id)
    workflow = gc3pie.retrieve_jobs(experiment_id, 'workflow')
    status = gc3pie.get_status_of_submitted_jobs(workflow, 2)
    return jsonify({
        'data': status
    })


@api.route(
    '/experiments/<experiment_id>/workflow/status/jobs', methods=['GET']
)
@jwt_required()
@assert_query_params('step_name', 'index')
@decode_query_ids()
def get_jobs_status(experiment_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/workflow/jobs

        Query the status of n jobs currently associated with step starting from a
        given index.


        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": [
                    {
                        "name": "Job X1",
                        "state": "RUNNING",
                        "exitcode": null,
                        "memory": 1024,
                        "time": "1:21:33"
                    },
                    ...
                ]
            }

        :query step_name: the name of the step (required)
        :query index: the index of the first job queried (required)
        :query batch_size: the amount of job stati to return starting from ``index``.
        :statuscode 200: no error

    """
    step_name = request.args.get('step_name')
    index = request.args.get('index', type=int)
    batch_size = request.args.get('batch_size', 50, type=int)

    # If the index is negative don't send `batch_size` jobs.
    # For example, if the index is -5 and the batch_size 50,
    # send the first 45 jobs back.
    if index < 0:
        batch_size = batch_size + index
        index = 0
        if batch_size <= 0:
            return jsonify({
                'data': []
            })

    logger.info(
        'get status of jobs starting from index #%d of step "%s" for experiment %d',
        index, step_name, experiment_id
    )
    submission_id = gc3pie.get_id_of_last_submission(experiment_id, 'workflow')
    # TODO: Upon reload, the submission_id of tasks doesn't get updated.
    # While this makes sense to track tasks belonging to the same collection
    # it doesn't allow the differentiation of submissions (as the name implies).
    with tm.utils.MainSession() as session:
        step_task_id = session.query(tm.Task.id).\
            filter(
                tm.Task.submission_id == submission_id,
                tm.Task.name == step_name,
                tm.Task.is_collection
            ).\
            one_or_none()
        if step_task_id is None:
            status = []
        else:
            step = gc3pie.retrieve_single_job(step_task_id)
            if len(step.tasks) == 0:
                status = []
            else:
                task_ids = []
                for phase in step.tasks:
                    if hasattr(phase, 'tasks'):
                        if hasattr(phase.tasks[0], 'tasks'):
                            for subphase in phase.tasks:
                                task_ids.extend([
                                    t.persistent_id for t in subphase.tasks
                                ])
                        else:
                            task_ids.extend([
                                t.persistent_id for t in phase.tasks
                            ])
                    else:
                        task_ids.append(phase.persistent_id)
                tasks = session.query(tm.Task).\
                    filter(
                        tm.Task.id.in_(task_ids),
                        ~tm.Task.is_collection
                    ).\
                    order_by(tm.Task.id).\
                    limit(batch_size).\
                    offset(index).\
                    all()
                status = [t.status for t in tasks]

    return jsonify({
        'data': status
    })


@api.route('/experiments/<experiment_id>/workflow/description', methods=['GET'])
@jwt_required()
@decode_query_ids()
def get_workflow_description(experiment_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/workflow/description

        Get the workflow description for the experiment with id ``experiment_id``.
        Please refer to the respective documentation to see how such description objects
        are structured.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": {...}
            }

        :statuscode 200: no error

    """
    logger.info('get workflow description for experiment %d', experiment_id)
    with tm.utils.MainSession() as session:
        experiment = session.query(tm.ExperimentReference).get(experiment_id)
        description = experiment.workflow_description
    return jsonify({
        'data': description.to_dict()
    })


@api.route('/experiments/<experiment_id>/workflow/description', methods=['POST'])
@jwt_required()
@assert_form_params('description')
@decode_query_ids()
def save_workflow_description(experiment_id):
    """
    .. http:post:: /api/experiments/(string:experiment_id)/workflow/description

        Save a new workflow description for the specified experiment.

        **Example request**:

            Content-Type: application/json

            {
                "description": {...}
            }

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "message": "ok"
            }

        :statuscode 200: no error

    """
    logger.info('save workflow description for experiment %d', experiment_id)
    data = request.get_json()
    workflow_description = WorkflowDescription(**data['description'])
    with tm.utils.MainSession() as session:
        experiment = session.query(tm.ExperimentReference).\
            get(experiment_id)
        experiment.persist_workflow_description(workflow_description)
    return jsonify({
        'message': 'ok'
    })


@api.route('/experiments/<experiment_id>/workflow/kill', methods=['POST'])
@jwt_required()
@decode_query_ids()
def kill_workflow(experiment_id):
    """
    .. http:post:: /api/experiments/(string:experiment_id)/workflow/kill

        Kill all jobs of the currently running workflow.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "message": "ok"
            }

        :statuscode 200: no error

    """
    logger.info('kill workflow for experiment %d', experiment_id)
    workflow = gc3pie.retrieve_jobs(experiment_id, 'workflow')
    gc3pie.kill_jobs(workflow)
    return jsonify({
        'message': 'ok'
    })


@api.route('/experiments/<experiment_id>/workflow/log', methods=['POST'])
@jwt_required()
@assert_form_params('job_id')
@decode_query_ids()
def get_job_log_output(experiment_id):
    """
    .. http:post:: /api/experiments/(string:experiment_id)/workflow/log

        Get the log file for a specific job.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "message": "ok",
                "stdout": string,
                "stderr": string
            }

        :statuscode 200: no error

    """
    data = request.get_json()
    job_id = data['job_id']
    logger.info(
        'get job log output for experiment %d and job %d',
        experiment_id, job_id
    )
    # NOTE: This is the persistent task ID of the job
    job = gc3pie.retrieve_single_job(job_id)
    stdout_file = os.path.join(job.output_dir, job.stdout)
    with open(stdout_file, 'r') as f:
        out = f.read()
    stderr_file = os.path.join(job.output_dir, job.stderr)
    with open(stderr_file, 'r') as f:
        err = f.read()
    return jsonify({
        'message': 'ok',
        'stdout': out,
        'stderr': err
    })


