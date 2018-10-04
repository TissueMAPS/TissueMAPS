# TmServer - TissueMAPS server application.
# Copyright (C) 2016-2018 University of Zurich
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
"""API view functions for querying :mod:`workflow <tmlib.workflow>`
resources.
"""
import json
import collections
import os
from cStringIO import StringIO
import logging
import numpy as np
from flask import jsonify, send_file, current_app, request
from flask_jwt import jwt_required
from flask_jwt import current_identity
from sqlalchemy import func

import tmlib.models as tm
from tmlib.workflow.workflow import Workflow
from tmlib.workflow.description import WorkflowDescription
from tmlib.workflow.submission import SubmissionManager
from tmlib.workflow.utils import format_task_data
from tmlib.workflow.jterator.api import ImageAnalysisPipelineEngine
from tmlib.workflow.jterator.description import (
    PipelineDescription, HandleDescriptions
)

from tmserver.util import (
    decode_query_ids, decode_form_ids, assert_query_params, assert_form_params
)
from tmserver.model import encode_pk
from tmserver.extensions import gc3pie
from tmserver.api import api
from tmserver.error import *
from tmserver import cfg as server_cfg


logger = logging.getLogger(__name__)


def _retrieve_experiment_or_abort(experiment_id, session):
    """
    Return the `Experiment`:class: instance corresponding to *experiment_id*.

    Argument *session* must be an instance of
    `tmlib.models.utils.ExperimentSession`:class: which is queried for
    retrieving the `Experiment`:class: instance.

    :raise tmserver.error.ResourceNotFoundError:
      If no experiment with the given ID can be found.
    """
    experiment = session.query(tm.Experiment).get(experiment_id)
    if experiment is None:
        raise ResourceNotFoundError(tm.Experiment, experiment_id=experiment_id)
    return experiment


@api.route('/experiments/<experiment_id>/workflow/submit', methods=['POST'])
@jwt_required()
@decode_query_ids('write')
def submit_workflow(experiment_id):
    """
    .. http:post:: /api/experiments/(string:experiment_id)/workflow/submit

        Submit a workflow based on a ``WorkflowDescription``.
        Please refer to the respective class documention for more details on how to
        structure such a description object.

        **Example request**:

        .. sourcecode:: http

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

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error

    """
    logger.info('submit workflow for experiment %d', experiment_id)
    data = request.get_json()
    with tm.utils.ExperimentSession(experiment_id) as session:
        experiment = _retrieve_experiment_or_abort(experiment_id, session)
        if 'description' in data:
            logger.info('use provided workflow description')
            workflow_description = WorkflowDescription(**data['description'])
            experiment.persist_workflow_description(workflow_description)
        else:
            logger.warn('no workflow description provided')
            logger.info('load workflow description')
            workflow_description = experiment.workflow_description
        workflow_type = experiment.workflow_type
    submission_manager = SubmissionManager(experiment_id, 'workflow')
    submission_id, user_name = submission_manager.register_submission()
    workflow = Workflow(
        experiment_id=experiment_id,
        verbosity=server_cfg.logging_verbosity,
        submission_id=submission_id,
        user_name=user_name,
        description=workflow_description
    )
    gc3pie.store_task(workflow)
    gc3pie.submit_task(workflow)

    return jsonify({
        'message': 'ok',
        'submission_id': workflow.submission_id
    })


@api.route('/experiments/<experiment_id>/workflow/resubmit', methods=['POST'])
@jwt_required()
@decode_query_ids('write')
def resubmit_workflow(experiment_id):
    """
    .. http:post:: /api/experiments/(string:experiment_id)/workflow/resubmit

        Resubmit a workflow for an experiment providing a new
        :class:`WorkflowDescription <tmlib.workflow.description.WorkflowDescription>`
        in YAML format and optionally an ``index`` of a stage at which the
        workflow should be resubmitted.

        **Example request**:

        .. sourcecode:: http

            Content-Type: application/json

            {
                "description": {...},
                "index": 1
            }

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "message": "ok",
                "submission_id": 1
            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 400: malformed request
        :statuscode 200: no error

    """
    logger.info('resubmit workflow for experiment %d', experiment_id)
    data = json.loads(request.data)
    index = data.get('index')
    stage_name = data.get('stage_name')
    with tm.utils.ExperimentSession(experiment_id) as session:
        experiment = _retrieve_experiment_or_abort(experiment_id, session)
        if 'description' in data:
            logger.info('use provided workflow description')
            workflow_description = WorkflowDescription(**data['description'])
            experiment.persist_workflow_description(workflow_description)
        else:
            logger.info('load workflow description')
            workflow_description = experiment.workflow_description
    if stage_name is None and index is None:
        index = 0
    elif index is not None:
        index = int(index)
    elif stage_name is not None:
        indices = [
            i for i, d in enumerate(workflow_description.stages)
            if d.name == stage_name and d.active
        ]
        if len(indices) == 0:
            raise MalformedRequestError(
                'The specified stage "%s" does not exist or is not set active.'
                % stage_name
            )
        index = indices[0]
    else:
        raise MalformedRequestError(
            'Only one of the following parameters can be specified in the '
            'request body: "index", "stage_name"'
        )
    workflow = gc3pie.retrieve_most_recent_task(experiment_id, 'workflow')
    # sanity check -- the job daemon will report the same error, but
    # at that point it'd be too late to report to HTTP API clients
    total_stages = len(workflow.tasks)
    if index <= total_stages:
        if (index > 0 and not workflow.tasks[index-1].is_terminated):
            raise MalformedRequestError(
                'Cannot resubmit workflow from stage %d:'
                ' the preceding stage (task ID %s)'
                ' has not completed running yet.'
                % (index, workflow.tasks[index-1].persistent_id)
            )
    else:
        raise MalformedRequestError(
            'Workflow has only %d stages, cannot resubmit from stage %d'
            % (total_stages, index)
        )
    workflow.update_description(workflow_description)
    workflow.update_stage(index)
    gc3pie.resubmit_task(workflow, index)
    return jsonify({
        'message': 'ok',
        'submission_id': workflow.submission_id
    })


@api.route('/experiments/<experiment_id>/workflow/status', methods=['GET'])
@jwt_required()
@decode_query_ids('read')
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

        :query depth: number of subtasks that should be queried (optional, default: 2)

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error

    """
    logger.info('get workflow status for experiment %d', experiment_id)
    depth = request.args.get('depth', 2, type=int)
    workflow_id = gc3pie.get_id_of_most_recent_task(experiment_id, 'workflow')
    if workflow_id is not None:
        status = gc3pie.get_task_status(workflow_id, depth)
    else:
        status = None
    return jsonify(data=status)


@api.route(
    '/experiments/<experiment_id>/workflow/jobs/<job_id>/log', methods=['GET']
)
@jwt_required()
@decode_query_ids('read')
def get_job_log(experiment_id, job_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/workflow/jobs/(string:job_id)/log

        Get the log output of a
        :class:`WorkflowStepJob <tmlib.workflow.jobs.WorkflowStepJob>`.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": {
                    "stdout": string,
                    "stderr": string
                }
            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error

    """
    logger.info(
        'get job log output for experiment %d and job %d',
        experiment_id, job_id
    )
    # NOTE: This is the persistent task ID of the job
    job = gc3pie.retrieve_task(job_id)
    stdout_file = os.path.join(job.output_dir, job.stdout)
    with open(stdout_file, 'r') as f:
        out = f.read()
    stderr_file = os.path.join(job.output_dir, job.stderr)
    with open(stderr_file, 'r') as f:
        err = f.read()
    return jsonify(data={'stdout': out, 'stderr': err})


@api.route('/experiments/<experiment_id>/workflow/jobs', methods=['GET'])
@jwt_required()
@decode_query_ids('read')
def get_workflow_jobs(experiment_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/workflow/jobs

        Query the status of jobs for a given
        :class:`WorkflowStep <tmlib.workflow.workflow.WorkflowStep>`.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": [
                    {
                        "id": "dG1hcHM3NzYxOA==",
                        "name": "metaconfig_run_000001",
                        "state": "RUNNING",
                        "exitcode": 0,
                        "memory": 1024,
                        "time": "1:21:33"
                        "cpu_time": "1:14:12"
                    },
                    ...
                ]
            }

        :query step_name: name of the workflow step for which jobs should be queried (required)
        :query step_phase: name of the workflow step phase for which jobs should be queried (optional)
        :query name: name of the job (optional)
        :query index: the index of the first job queried (optional)
        :query batch_size: the amount of job stati to return starting from ``index`` (optional)

        :reqheader Authorization: JWT token issued by the server
        :statuscode 400: malformed request
        :statuscode 200: no error

    .. note:: Parameters ``index`` and ``batch_size`` can only be used togethger.
        Parameters ``name`` and ``step_phase`` are exclusive and cannot be
        combined with ``index`` and ``batch_size``.
    """
    step_name = request.args.get('step_name')
    logger.info(
        'get status of jobs for workflow step "%s" of experiment %d',
        step_name, experiment_id
    )
    step_phase = request.args.get('phase')
    name = request.args.get('name')
    index = request.args.get('index', type=int)
    batch_size = request.args.get('batch_size', type=int)

    if ((index is not None and batch_size is None) or
            (index is None and batch_size is not None)):
        raise MalformedRequestError(
            'Either both or none of the following parameters must be specified: '
            '"index", "batch_size"'
        )
    if index is not None and name is not None:
        raise MalformedRequestError(
            'Only one of the following parameters can be specified: '
            '"name", "index"'
        )
    if batch_size is not None and name is not None:
        raise MalformedRequestError(
            'Only one of the following parameters can be specified: '
            '"name", "batch_size"'
        )
    if step_phase is not None and name is not None:
        raise MalformedRequestError(
            'Only one of the following parameters can be specified: '
            '"name", "step_phase"'
        )

    # If the index is negative don't send `batch_size` jobs.
    # For example, if the index is -5 and the batch_size 50,
    # send the first 45 jobs back.
    if index is not None and batch_size is not None:
        if index < 0 and batch_size is not None:
            batch_size = batch_size + index
            index = 0
            if batch_size <= 0:
                return jsonify(data=[])

    submission_id = gc3pie.get_id_of_most_recent_submission(
        experiment_id, 'workflow'
    )
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
            phase_tasks = session.query(tm.Task.id, tm.Task.name).\
                filter_by(parent_id=step_task_id).\
                all()
            if len(phase_tasks) == 0:
                status = []
            else:
                task_ids = collections.defaultdict(list)
                for phase_id, phase_name in phase_tasks:
                    if step_phase is not None:
                        if not phase_name.endswith(step_phase):
                            continue
                    subtasks = session.query(
                            tm.Task.id, tm.Task.is_collection, tm.Task.name
                        ).\
                        filter_by(parent_id=phase_id).\
                        order_by(tm.Task.id).\
                        all()
                    if len(subtasks) == 0:
                        continue
                    else:
                        for st in subtasks:
                            if st.is_collection:
                                subsubtasks = session.query(
                                        tm.Task.id, tm.Task.name
                                    ).\
                                    filter_by(parent_id=st.id).\
                                    order_by(tm.Task.id).\
                                    all()
                                for sst in subsubtasks:
                                    task_ids[sst.name].append(sst.id)
                            else:
                                task_ids[st.name].append(st.id)

                task_ids = [v[0] for v in task_ids.values()]
                if task_ids:
                    tasks = session.query(
                            tm.Task.id, tm.Task.name, tm.Task.type,
                            tm.Task.state, tm.Task.created_at,
                            tm.Task.updated_at, tm.Task.exitcode,
                            tm.Task.memory, tm.Task.time, tm.Task.cpu_time
                        ).\
                        filter(tm.Task.id.in_(task_ids)).\
                        order_by(tm.Task.name)
                    if index is not None and batch_size is not None:
                        logger.debug(
                            'query status of %d jobs starting at %d',
                            batch_size, index
                        )
                        tasks = tasks.limit(batch_size).offset(index)
                    if name is not None:
                        tasks = tasks.filter_by(name=name)
                    tasks = tasks.all()
                    status = []
                    for t in tasks:
                        s = format_task_data(
                            t.name, t.type, t.created_at, t.updated_at,
                            t.state, t.exitcode, t.memory, t.time, t.cpu_time
                        )
                        s['id'] = encode_pk(t.id)
                        status.append(s)
                else:
                    status = []

    return jsonify(data=status)


@api.route('/experiments/<experiment_id>/workflow/description', methods=['GET'])
@jwt_required()
@decode_query_ids('read')
def get_workflow_description(experiment_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/workflow/description

        Get the persisted
        :class:`WorkflowDescription <tmlib.workflow.description.WorkflowDescription>`.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": {...}
            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error

    """
    logger.info('get workflow description for experiment %d', experiment_id)
    with tm.utils.ExperimentSession(experiment_id) as session:
        experiment = _retrieve_experiment_or_abort(experiment_id, session)
        description = experiment.workflow_description
    return jsonify(data=description.to_dict())


@api.route('/experiments/<experiment_id>/workflow/description', methods=['POST'])
@jwt_required()
@assert_form_params('description')
@decode_query_ids('write')
def update_workflow_description(experiment_id):
    """
    .. http:post:: /api/experiments/(string:experiment_id)/workflow/description

        Upload a
        :class:`WorkflowDescription <tmlib.workflow.description.WorkflowDescription>`.

        **Example request**:

        .. sourcecode:: http

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

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error

    """
    logger.info('save workflow description for experiment %d', experiment_id)
    data = request.get_json()
    workflow_description = WorkflowDescription(**data['description'])
    with tm.utils.ExperimentSession(experiment_id) as session:
        experiment = _retrieve_experiment_or_abort(experiment_id, session)
        experiment.persist_workflow_description(workflow_description)
    return jsonify(message='ok')


@api.route('/experiments/<experiment_id>/workflow/kill', methods=['POST'])
@jwt_required()
@decode_query_ids('write')
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

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error

    """
    logger.info('kill workflow for experiment %d', experiment_id)
    workflow = gc3pie.retrieve_most_recent_task(experiment_id, 'workflow')
    gc3pie.kill_task(workflow)
    return jsonify(message='ok')


@api.route('/experiments/<experiment_id>/workflow/jtproject', methods=['GET'])
@jwt_required()
@decode_query_ids()
def get_jterator_project(experiment_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/workflow/jtproject

        Get a jterator project consisting of a
        :class:`PipelineDescription <tmlib.workflow.jterator.description.PipelineDescription>`
        and an optional
        :class:`HandleDescriptions <tmlib.workflow.jterator.description.HandleDescriptions>`.
        for each module of the pipeline.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": {
                    "pipeline": {
                        "input": {
                            "channels": [
                                {
                                    "name": "wavelength-1"
                                }
                            ],
                            "objects": []
                        },
                        "output": {
                            "objects": []
                        },
                        "pipeline": [
                            {
                                "handles": ../handles/module1.handles.yaml,
                                "source": module1.py
                                "active": true
                            }
                        ]

                    },
                    "handles": {
                        "module1": {
                            "version": 0.1.0,
                            "input": [],
                            "output": []
                        },
                        ...
                    }
                }
            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error

    """
    logger.info('get jterator project of experiment %d', experiment_id)
    jt = ImageAnalysisPipelineEngine(experiment_id)
    pipeline_description = jt.project.pipe.description.to_dict()
    handles_descriptions = {}
    for h in jt.project.handles:
        handles = h.to_dict()
        handles_descriptions[handles['name']] = handles['description']
    return jsonify(data={
        'pipeline': pipeline_description,
        'handles': handles_descriptions
    })


@api.route('/experiments/<experiment_id>/workflow/jtproject', methods=['PUT'])
@jwt_required()
@assert_form_params('pipeline', 'handles')
@decode_query_ids()
def update_project(experiment_id):
    '''
    .. http:put:: /api/experiments/(string:experiment_id)/workflow/jtproject

        Update a jterator project consisting of a
        :class:`PipelineDescription <tmlib.workflow.jterator.description.PipelineDescription>`
        and an optional
        :class:`HandleDescriptions <tmlib.workflow.jterator.description.HandleDescriptions>`
        for each module in the pipeline.

        **Example request**:

        .. sourcecode:: http

            Content-Type: application/json

            {
                "pipeline": {
                    "input": {
                        "channels": [
                            {
                                "name": "wavelength-1"
                            }
                        ]
                    },
                    "output": {},
                    "pipeline": [
                        {
                            "handles": ../handles/module1.handles.yaml,
                            "source": module1.py
                            "active": true
                        }
                    ]

                },
                "handles": {
                    "module1": {
                        "version": 0.1.0,
                        "input": [],
                        "output": []
                    },
                    ...
                }
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
    '''
    logger.info('update jterator project of experiment %d', experiment_id)
    data = json.loads(request.data)
    pipeline = data.get('pipeline')
    handles = data.get('handles')
    logger.debug('read pipeline description')
    pipeline_description = PipelineDescription(**pipeline)
    handles_descriptions = dict()
    for name, description in handles.iteritems():
        logger.debug('read handles description for module "%s"', name)
        handles_descriptions[name] = HandleDescriptions(**description)

    jt = ImageAnalysisPipelineEngine(
        experiment_id,
        pipeline_description=pipeline_description,
        handles_descriptions=handles_descriptions,
    )
    jt.project.save()
    return jsonify(message='ok')
