# TmServer - TissueMAPS server application.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
# Copyright (C) 2018  University of Zurich
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
"""API view functions for :mod:`experiment <tmlib.models.experiment>`
resources.
"""
import json
import os
from cStringIO import StringIO
import logging
import numpy as np
from flask import jsonify, send_file, current_app, request
from flask_jwt import jwt_required, current_identity
from werkzeug import secure_filename
from sqlalchemy import or_

import tmlib.models as tm
from tmlib.workflow.dependencies import get_workflow_type_information
from tmlib.workflow.metaconfig import SUPPORTED_MICROSCOPE_TYPES
from tmlib.models.plate import SUPPORTED_PLATE_AQUISITION_MODES
from tmlib import cfg as lib_cfg

from tmserver.util import (
    decode_query_ids, decode_form_ids, is_true, is_false,
    assert_query_params, assert_form_params
)
from tmserver.model import encode_pk
from tmserver.extensions import gc3pie
from tmserver.api import api
from tmserver.error import *


logger = logging.getLogger(__name__)


@api.route('/workflow_types', methods=['GET'])
@jwt_required()
def get_workflow_types():
    """
    .. http:get:: /api/workflow_types

        Get a list of implemented workflow types.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": [
                    "canonical", "multiplexing"
                ]
            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error

        .. seealso::

            :func:`tmlib.workflow.get_workflow_type_information`

    """
    logger.info('get list of implemented workflow types')
    return jsonify(data=list(get_workflow_type_information()))


@api.route('/microscope_types', methods=['GET'])
@jwt_required()
def get_microscope_types():
    """
    .. http:get:: /api/microscope_types

        Get a list of implemented microscope types.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": [
                    "visiview", "cellvoyager"
                ]
            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error

        .. seealso::

            :class:`tmlib.workflow.metaconfig.SUPPORTED_MICROSCOPE_TYPES`

    """
    logger.info('get list of implemented microscope types')
    return jsonify({
        'data': list(SUPPORTED_MICROSCOPE_TYPES)
    })


@api.route('/acquisition_modes', methods=['GET'])
@jwt_required()
def get_acquisition_modes():
    """
    .. http:get:: /api/acquisition_modes

        Get a list of all implemented plate acquisition modes.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": ["basic", "multiplexing"]
            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error

        .. seealso::

            :class:`tmlib.models.plate.SUPPORTED_PLATE_AQUISITION_MODES`

    """
    logger.info('get list of supported plate acquisition modes')
    return jsonify({
        'data': list(SUPPORTED_PLATE_AQUISITION_MODES)
    })


@api.route('/experiments', methods=['GET'])
@jwt_required()
def get_experiments():
    """
    .. http:get:: /api/experiments

        Get experiments for the currently logged in user.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": [
                    {
                        "id": "MQ==",
                        "name": "Experiment XY",
                        "description": "Optional experiment description",
                        "user": "Testuser"
                    },
                    ...
                ]
            }

        :query name: name of an experiment (optional)

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 404: no such experiment found

    """
    logger.info('get experiments')
    experiment_name = request.args.get('name')
    with tm.utils.MainSession() as session:
        shares = session.query(tm.ExperimentShare.experiment_id).\
            filter_by(user_id=current_identity.id).\
            all()
        shared_ids = [s.experiment_id for s in shares]
        if shared_ids:
            experiments = session.query(tm.ExperimentReference).\
                filter(
                    or_(
                        tm.ExperimentReference.user_id == current_identity.id,
                        tm.ExperimentReference.id.in_(shared_ids)
                    )
                )
        else:
            experiments = session.query(tm.ExperimentReference).\
                filter_by(user_id=current_identity.id)
        if experiment_name is not None:
            logger.info('filter experiments for name "%s"', experiment_name)
            experiments = experiments.filter_by(name=experiment_name)
        experiments = experiments.all()
        return jsonify(data=experiments)


@api.route('/experiments/<experiment_id>', methods=['GET'])
@jwt_required()
@decode_query_ids('read')
def get_experiment(experiment_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)

        Get the experiment with the hashed id ``experiment_id``.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": {
                    "id": "MQ==",
                    "name": "Experiment XY",
                    "description": "Optional experiment description",
                    "user": "Testuser"
                }
            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 404: no such experiment found

    """
    logger.info('get experiment %d', experiment_id)
    with tm.utils.MainSession() as session:
        experiment = session.query(tm.ExperimentReference).get(experiment_id)
        return jsonify({
            'data': experiment
        })


@api.route('/experiments', methods=['POST'])
@jwt_required()
@assert_form_params(
    'name', 'workflow_type', 'microscope_type', 'plate_format',
    'plate_acquisition_mode'
)
def create_experiment():
    """
    Create a new :class:`Experiment <tmlib.models.experiment.Experiment>`.

    .. note::

      The ``description`` parameter in this request is *not* the
      "workflow description" YAML file: the latter is set to a default
      value (depending on the ``workflow_type`` key) and can be later
      changed with the ``update_workflow_description()``:func: API call; the
      former is only used to set the ``description`` columnt in table
      ``experiment_references`` which is used when listing existing
      experiments in the UI.

    .. http:post:: /api/experiments


        **Example request**:

        .. sourcecode:: http

            Content-Type: application/json

            {
                "name": "Experiment XY",
                "description": "Optional description",
                "workflow_type": "canonical",
                "plate_format": "0",
                "plate_acquisition_mode": "multiplexing",
                "microscope_type": "cellvoyager"
            }

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": {
                    "id": "MQ==",
                    "name": "Experiment XY",
                    "description": "Optional description",
                    "user": "Testuser"
                }
            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
    """
    data = request.get_json()
    name = data.get('name')
    workflow_type = data.get('workflow_type')
    microscope_type = data.get('microscope_type')
    plate_format = int(data.get('plate_format'))
    plate_acquisition_mode = data.get('plate_acquisition_mode')
    # WARNING: this description is just human-readable text,
    # has no connection to the "workflow description" YAML file
    description = data.get('description', '')
    logger.info('create experiment "%s"', name)
    with tm.utils.MainSession() as session:
        experiment_ref = tm.ExperimentReference(
            name=name,
            description=description,
            user_id=current_identity.id,
            root_directory=lib_cfg.storage_home
        )
        session.add(experiment_ref)
        session.commit()
        experiment_id = experiment_ref.id
        experiment_location = experiment_ref.location

    with tm.utils.ExperimentSession(experiment_id) as session:
        experiment = tm.Experiment(
            id=experiment_id,
            location=experiment_location,
            workflow_type=workflow_type,
            microscope_type=microscope_type,
            plate_format=plate_format,
            plate_acquisition_mode=plate_acquisition_mode
        )
        session.add(experiment)

    return jsonify({
        'data': {
            'id': encode_pk(experiment_id),
            'name': name,
            'description': description,
            'user': current_identity.name
        }
    })


@api.route(
    '/experiments/<experiment_id>', methods=['PUT']
)
@jwt_required()
@decode_query_ids('read')
def update_experiment(experiment_id):
    """
    .. http:put:: /api/experiments/(string:experiment_id)

        Update an :class:`Experiment <tmlib.models.experiment.Experiment>`.

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
    logger.info('rename experiment %d', experiment_id)
    with tm.utils.MainSession() as session:
        experiment = session.query(tm.ExperimentReference).get(experiment_id)
        experiment.name = name
    return jsonify(message='ok')


@api.route('/experiments/<experiment_id>', methods=['DELETE'])
@jwt_required()
@decode_query_ids('write')
def delete_experiment(experiment_id):
    """
    .. http:delete:: /api/experiments/(string:experiment_id)

        Delete a specific
        :class:`Experiment <tmlib.models.experiment.Experiment>`.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "message": "ok"
            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 401: not authorized

    """
    logger.info('delete experiment %d', experiment_id)
    workflow = gc3pie.retrieve_most_recent_task(experiment_id, 'workflow')
    if workflow is not None:
        gc3pie.kill_task(workflow)
    with tm.utils.MainSession() as session:
        experiment = session.query(tm.ExperimentReference).get(experiment_id)
        session.query(tm.ExperimentReference).\
            filter_by(id=experiment_id).\
            delete()
    return jsonify(message='ok')
