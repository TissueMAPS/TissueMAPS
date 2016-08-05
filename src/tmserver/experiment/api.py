import json
import os
import cv2
from cStringIO import StringIO
import logging

import numpy as np
from flask import jsonify, send_file, current_app, request
from flask.ext.jwt import jwt_required
from flask.ext.jwt import current_identity
from werkzeug import secure_filename

import tmlib.models as tm
from tmlib.workflow.description import WorkflowDescription
from tmlib.workflow.submission import SubmissionManager
from tmlib.workflow.tmaps.api import WorkflowManager
from tmlib.image import PyramidTile
from tmlib.workflow.metaconfig import SUPPORTED_MICROSCOPE_TYPES
from tmlib.models.plate import SUPPORTED_PLATE_AQUISITION_MODES

from tmserver.util import extract_model_from_path, assert_request_params
from tmserver.model import decode_pk
from tmserver.model import encode_pk
from tmserver.extensions import db
from tmserver.extensions import gc3pie
from tmserver.api import api
from tmserver.error import (
    MalformedRequestError,
    MissingGETParameterError,
    MissingPOSTParameterError,
    ResourceNotFoundError,
    NotAuthorizedError
)

logger = logging.getLogger(__name__)

def _raise_error_when_missing(arg):
    raise MissingGETParameterError(arg)

@api.route(
    '/experiments/<experiment_id>/channel_layers/<channel_layer_id>/tiles',
    methods=['GET']
)
@extract_model_from_path(tm.Experiment, tm.ChannelLayer)
@assert_request_params('x', 'y', 'z')
def get_image_tile(experiment, channel_layer):
    """Sends a tile image for a specific layer.
    This route is accessed by openlayers."""
    x = request.args.get('x', type=int)
    y = request.args.get('y', type=int)
    z = request.args.get('z', type=int)

    logger.debug(
        'get image tile: x=%d, y=%d, z=%d, zplane=%d, tpoint=%d',
        x, y, z, channel_layer.zplane, channel_layer.tpoint
    )

    tile_file = db.session.query(tm.PyramidTileFile).filter_by(
        column=x, row=y, level=z, channel_layer_id=channel_layer.id
    ).one_or_none()
    if tile_file is None:
        raise ResourceNotFoundError(
            'Tile not found: column=%d, row=%d, level=%d' % (x, y, z)
        )
        logger.warn('file does not exist - send empty image')
        f = StringIO()
        img = PyramidTile.create_as_background()
        f.write(cv2.imencode('.jpeg', img.array))
        f.seek(0)
        return send_file(f, mimetype='image/jpeg')
    return send_file(tile_file.location)


@api.route('/experiments/<experiment_id>/cycles/id', methods=['GET'])
@jwt_required()
@extract_model_from_path(tm.Experiment)
@assert_request_params('plate_name', 'cycle_index')
def get_cycle_id(experiment):
    experiment_name = experiment.name
    plate_name = request.args.get('plate_name')
    cycle_index = request.args.get('cycle_index', type=int)
    cycle = db.session.query(tm.Cycle).\
        join(tm.Plate).\
        filter(
            tm.Plate.name == plate_name,
            tm.Plate.experiment_id == experiment.id,
            tm.Cycle.index == cycle_index,
        ).\
        one()
    return jsonify({
        'id': encode_pk(cycle.id)
    })


@api.route('/experiments/<experiment_id>/channels/id', methods=['GET'])
@jwt_required()
@extract_model_from_path(tm.Experiment)
@assert_request_params('channel_name')
def get_channel_id(experiment):
    channel_name = request.args.get('channel_name')
    channel = db.session.query(tm.Channel).\
        filter_by(name=channel_name, experiment_id=experiment.id).\
        one()
    return jsonify({
        'id': encode_pk(channel.id)
    })


@api.route('/experiments/<experiment_id>/channel_layers/id', methods=['GET'])
@jwt_required()
@extract_model_from_path(tm.Experiment)
@assert_request_params('channel_name', 'tpoint', 'zplane')
def get_channel_id(experiment):
    channel_name = request.args.get('channel_name')
    tpoint = request.args.get('tpoint', type=int)
    zplane = request.args.get('zplane', type=int)
    channel_layer = db.session.query(tm.ChannelLayer).\
        join(tm.Channel).\
        filter(
            tm.Channel.name == channel_name,
            tm.Channel.experiment_id == experiment.id,
            tm.ChannelLayer.tpoint == tpoint,
            tm.ChannelLayer.zplane == zplane,
        ).\
        one()
    return jsonify({
        'id': encode_pk(channel_layer.id)
    })


@api.route(
    '/experiments/<experiment_id>/channels/<channel_name>/image-files',
    methods=['GET']
)
@jwt_required()
@extract_model_from_path(tm.Experiment)
@assert_request_params(
    'plate_name', 'cycle_index', 'well_name', 'x', 'y', 'tpoint', 'zplane'
)
def get_channel_image(experiment, channel_name):
    channel_name = request.args.get('plate_name')
    well_name = request.args.get('well_name')
    x = request.args.get('x', type=int)
    y = request.args.get('y', type=int)
    channel_name = request.args.get('cycle_index', type=int)
    tpoint = request.args.get('tpoint', type=int)
    zplane = request.args.get('zplane', type=int)
    illumcorr = request.args.get('correct', type=bool)
    site_id = db.session.query(tm.Site.id).\
        join(tm.Well).\
        joint(tm.Plate).\
        filter(
            tm.Plate.experiment_id == experiment.id,
            tm.Plate.name == plate_name,
            tm.Well.name == well_name,
            tm.Site.x == x, tm.Site.y == y
        ).\
        one()[0]
    channel_id = db.session.query(tm.Channel.id).\
        filter_by(experiment_id=experiment.id, name=channel_name).\
        one()[0]
    image_file = db.session.query(tm.ChannelImageFile).\
        join(tm.Cycle).\
        filter(
            tm.Cycle.index == cycle_index,
            tm.ChannelImageFile.site_id == site_id,
            tm.ChannelImageFile.channel_id == channel_id,
            tm.ChannelImageFile.tpoint == tpoint
        ).\
        one()
    img = image_file.get(zplane)
    if illumcorr:
        # TODO: cache for a limited amount of time to not having to load
        # the file repeatedly when user downloads multiple files
        logger.info('correct image for illumination artefacts')
        illumstats_file = db.session.query(tm.IllumstatsFile).\
            filter_by(channel_id=channel_id, cycle_id=cycle.id).\
            one_or_none()
        if illumstats_file is None:
            raise ResourceNotFoundError(
                'No illumination statistics file found for channel %d'
                % channel_id
            )
        stats = illumstats_file.get()
        img = img.correct(stats)
    img = img.align()
    f = StringIO()
    f.write(cv2.imencode('.png', img.array)[1])
    f.seek(0)
    filename = '%s_%s_x%.3d_y%.3d_z%.3d_t%.3d_%s.png' % (
        experiment.name, well_name, x, y, zplane, tpoint, channel_name
    )
    return send_file(
        f,
        attachment_filename=secure_filename(filename),
        mimetype='image/png',
        as_attachment=True
    )


@api.route('/experiments/<experiment_id>/features', methods=['GET'])
@jwt_required()
@extract_model_from_path(tm.Experiment, check_ownership=True)
def get_features(experiment):
    """Sends a list of feature objects.

    Request
    -------

    Required GET parameters:
        - experiment_id

    Response
    --------

    {
        "data": {
            mapobject_type_name: [
                {
                    "name": string
                },
                ...
            ],
            ...
        }
    }

    """
    features = db.session.query(tm.Feature).\
        filter_by(experiment_id=experiment.id).\
        all()
    if not features:
        logger.waring('no features found')
    return jsonify({
        'data': features
    })


@api.route('/microscope_types', methods=['GET'])
@jwt_required()
def get_microscope_types():
    """Gets all implemented microscope types.

    Response
    --------
    {
        "data": list of microscope types,
    }

    See also
    --------
    :py:class:`tmlib.workflow.metaconfig.SUPPORTED_MICROSCOPE_TYPES`
    """
    return jsonify({
        'data': list(SUPPORTED_MICROSCOPE_TYPES)
    })


@api.route('/acquisition_modes', methods=['GET'])
@jwt_required()
def get_acquisition_modes():
    """Gets all implemented plate acquisition modes.

    Response
    --------
    {
        "data": list of plate acquisition modes,
    }

    See also
    --------
    :py:class:`tmlib.models.plate.SUPPORTED_PLATE_AQUISITION_MODES`
    """
    return jsonify({
        'data': list(SUPPORTED_PLATE_AQUISITION_MODES)
    })



@api.route('/experiments', methods=['GET'])
@jwt_required()
def get_experiments():
    """Gets all experiments for the current user.

    Response
    --------
    {
        "data": list of experiment objects,
    }

    """
    return jsonify({
        'data': current_identity.experiments
    })


@api.route('/experiments/<experiment_id>', methods=['GET'])
@jwt_required()
@extract_model_from_path(tm.Experiment)
def get_experiment(experiment):
    """Gets an experiment by id.

    Response
    --------
    {
        "data": an experiment object serialized to json
    }

    """
    return jsonify({
        'data': experiment
    })


@api.route('/experiments/id', methods=['GET'])
@jwt_required()
@assert_request_params('experiment_name')
def get_experiment_id():
    """Gets the ID of an experiment given its name.

    Response
    --------
    {
        "data": an experiment ID serialized to json
    }

    """
    experiment_name = request.args.get('experiment_name')
    experiment = db.session.query(tm.Experiment).\
        filter_by(user_id=current_identity.id, name=experiment_name).\
        one()
    return jsonify({
        'id': encode_pk(experiment.id)
    })


@api.route('/experiments/<experiment_id>/workflow/submit', methods=['POST'])
@jwt_required()
@assert_request_params('description')
@extract_model_from_path(tm.Experiment)
def submit_workflow(experiment):
    logger.info('submit workflow')
    data = request.get_json()
    # data = json.loads(request.data)
    workflow_description = WorkflowDescription(**data['description'])
    experiment.persist_workflow_description(workflow_description)
    workflow_manager = WorkflowManager(experiment.id, 1)
    submission_manager = SubmissionManager(experiment.id, 'workflow')
    submission_id, user_name = submission_manager.register_submission()
    workflow = workflow_manager.create_workflow(
        submission_id, user_name, workflow_description
    )
    gc3pie.store_jobs(experiment, workflow)
    gc3pie.submit_jobs(workflow)

    return jsonify({
        'message': 'ok',
        'submission_id': workflow.submission_id
    })


@api.route('/experiments/<experiment_id>/workflow/resubmit', methods=['POST'])
@jwt_required()
@assert_request_params('description')
@extract_model_from_path(tm.Experiment)
def resubmit_workflow(experiment):
    logger.info('resubmit workflow')
    data = json.loads(request.data)
    index = data.get('index', 0)
    workflow_description = WorkflowDescription(**data['description'])
    workflow = gc3pie.retrieve_jobs(experiment, 'workflow')
    workflow.update_description(workflow_description)
    workflow.update_stage(index)
    gc3pie.resubmit_jobs(workflow, index)

    return jsonify({
        'message': 'ok',
        'submission_id': workflow.submission_id
    })


@api.route('/experiments/<experiment_id>/workflow/status', methods=['GET']) 
@jwt_required()
@extract_model_from_path(tm.Experiment)
def get_workflow_status(experiment):
    logger.info('get workflow status')
    workflow = gc3pie.retrieve_jobs(experiment, 'workflow')
    status = gc3pie.get_status_of_submitted_jobs(workflow)
    return jsonify({
        'data': status
    })


@api.route('/experiments/<experiment_id>/workflow/load', methods=['GET']) 
@jwt_required()
@extract_model_from_path(tm.Experiment)
def get_workflow_description(experiment):
    logger.info('get workflow description')
    description = experiment.workflow_description
    return jsonify({
        'data': description.as_dict()
    })


@api.route('/experiments/<experiment_id>/workflow/save', methods=['POST'])
@jwt_required()
@assert_request_params('description')
@extract_model_from_path(tm.Experiment)
def save_workflow_description(experiment):
    data = request.get_json()
    workflow_description = WorkflowDescription(**data['description'])
    experiment.persist_workflow_description(workflow_description)
    return jsonify({
        'message': 'ok'
    })


@api.route('/experiments/<experiment_id>/workflow/kill', methods=['POST'])
@jwt_required()
@extract_model_from_path(tm.Experiment)
def kill_workflow(experiment):
    logger.info('kill workflow')
    workflow = gc3pie.retrieve_jobs(experiment, 'workflow')
    gc3pie.kill_jobs(workflow)
    return jsonify({
        'message': 'ok'
    })


@api.route('/experiments/<experiment_id>/workflow/log', methods=['POST'])
@jwt_required()
@assert_request_params('id')
@extract_model_from_path(tm.Experiment)
def get_job_log_output(experiment):
    data = request.get_json()
    logger.info('get job log output')
    job = gc3pie.retrieve_single_job(data['id'])
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


@api.route('/experiments', methods=['POST'])
@jwt_required()
@assert_request_params(
    'name', 'description', 'plate_format', 'plate_acquisition_mode'
)
def create_experiment():
    data = request.get_json()
    name = data.get('name')
    description = data.get('description', '')
    microscope_type = data.get('microscope_type')
    plate_format = int(data.get('plate_format'))
    plate_acquisition_mode = data.get('plate_acquisition_mode')
    experiment = tm.Experiment(
        name=name,
        description=description,
        user_id=current_identity.id,
        microscope_type=microscope_type,
        plate_format=plate_format,
        root_directory=current_app.config['TMAPS_STORAGE_HOME'],
        plate_acquisition_mode=plate_acquisition_mode
    )
    db.session.add(experiment)
    db.session.commit()
    return jsonify({
        'data': experiment
    })


@api.route('/experiments/<experiment_id>', methods=['DELETE'])
@jwt_required()
@extract_model_from_path(tm.Experiment, check_ownership=True)
def delete_experiment(experiment):
    """Delete an experiment for the current user.

    Response
    --------
    {
        "message": 'Deletion ok'
    }

    """
    db.session.delete(experiment)
    db.session.commit()
    return jsonify(message='ok')


@api.route('/experiments/<experiment_id>/plates/<plate_id>', methods=['GET'])
@jwt_required()
@extract_model_from_path(tm.Experiment, tm.Plate, check_ownership=True)
def get_plate(experiment, plate):
    return jsonify(data=plate)


@api.route('/experiments/<experiment_id>/plates', methods=['GET'])
@jwt_required()
@extract_model_from_path(tm.Experiment, check_ownership=True)
def get_plates(experiment):
    """Get all plates for a specific experiment.

    Request
    -------

    Required GET parameters:
        - experiment_id

    Response
    --------

    {
        "data": [
            {
                "id": string,
                "name": string,
                "description": string,
                "experiment_id": number,
                "acquisition": Object
            },
            ...
        ]
    }

    """
    return jsonify(data=experiment.plates)


@api.route('/experiments/<experiment_id>/plates/<plate_id>', methods=['DELETE'])
@jwt_required()
@extract_model_from_path(tm.Experiment, tm.Plate, check_ownership=True)
def delete_plate(experiment, plate):
    db.session.delete(plate)
    db.session.commit()
    return jsonify(message='ok')


@api.route('/experiments/<experiment_id>/plates', methods=['POST'])
@jwt_required()
@assert_request_params('name')
@extract_model_from_path(tm.Experiment, check_ownership=True)
def create_plate(experiment):
    """
    Create a new plate for the experiment with id `experiment_id`.

    Request
    -------

    {
        name: string,
        description: string,
        experiment_id: string
    }

    Response
    --------

    Plate object

    """
    data = request.get_json()
    name = data.get('name')
    desc = data.get('description', '')
    plate = tm.Plate(
        name=name, description=desc,
        experiment_id=experiment.id
    )
    db.session.add(plate)
    db.session.commit()
    return jsonify(data=plate)


@api.route('/experiments/<experiment_id>/plates/id', methods=['GET'])
@jwt_required()
@assert_request_params('plate_name')
@extract_model_from_path(tm.Experiment, check_ownership=True)
def get_plate_id(experiment):
    plate_name = request.args.get('plate_name')
    plate = db.session.query(tm.Plate).\
        filter_by(name=plate_name, experiment_id=experiment.id).\
        one()
    return jsonify({
        'id': encode_pk(plate.id)
    })


@api.route('/experiments/<experiment_id>/acquisitions', methods=['POST'])
@jwt_required()
# @assert_request_params('plate_name', 'name')
@extract_model_from_path(tm.Experiment, check_ownership=True)
def create_acquisition(experiment):
    """
    Create a new acquisition for the plate with id `plate_id`.

    Request
    {
        name: string,
        description: string,
        plate_id: string
    }

    Response
    --------

    Acquisition object

    """
    data = request.get_json()
    plate_name = data.get('plate_name')
    name = data.get('name')
    desc = data.get('description', '')
    plate = db.session.query(tm.Plate).\
        filter_by(experiment_id=experiment.id, name=plate_name).\
        one_or_none()
    if plate is None:
        raise ResourceNotFoundError('Plate "%s" not found' % plate_name)
    acquisition = tm.Acquisition(
        name=name, description=desc,
        plate_id=plate.id
    )
    db.session.add(acquisition)
    db.session.commit()
    return jsonify(data=acquisition)


@api.route(
    '/experiments/<experiment_id>/acquisitions/<acquisition_id>',
    methods=['DELETE']
)
@jwt_required()
@extract_model_from_path(tm.Experiment, tm.Acquisition, check_ownership=True)
def delete_acquisition(experiment, acquisition):
    db.session.delete(acquisition)
    db.session.commit()
    return jsonify(message='ok')


@api.route(
    '/experiments/<experiment_id>/acquisitions/<acquisition_id>',
    methods=['GET']
)
@jwt_required()
@extract_model_from_path(tm.Experiment, tm.Acquisition, check_ownership=True)
def get_acquisition(experiment, acquisition):
    return jsonify(data=acquisition)


@api.route('/experiments/<experiment_id>/acquisitions/id', methods=['GET'])
@jwt_required()
@assert_request_params('plate_name', 'acquisition_name')
@extract_model_from_path(tm.Experiment)
def get_acquisition_id(experiment):
    plate_name = request.args.get('plate_name')
    acquisition_name = request.args.get('acquisition_name')
    acquisition = db.session.query(tm.Acquisition).\
        join(Plate).\
        filter(
            tm.Plate.experiment_id == experiment.id,
            tm.Plate.name == plate_name,
            tm.Acquisition.name == acquisition_name
        ).\
        one()
    return jsonify({
        'id': encode_pk(acquisition.id)
    })


@api.route(
    '/experiments/<experiment_id>/acquisitions/<acquisition_id>/image-files',
    methods=['GET']
)
@jwt_required()
@extract_model_from_path(tm.Experiment, tm.Acquisition, check_ownership=True)
def get_acquisition_image_files(experiment, acquisition):
    return jsonify({
        'data': acquisition.microscope_image_files
    })


@api.route(
    '/experiments/<experiment_id>/acquisitions/<acquisition_id>/metadata-files',
    methods=['GET']
)
@jwt_required()
@extract_model_from_path(tm.Experiment, tm.Acquisition, check_ownership=True)
def get_acquisition_metadata_files(experiment, acquisition):
    return jsonify({
        'data': acquisition.microscope_metadata_files
    })
