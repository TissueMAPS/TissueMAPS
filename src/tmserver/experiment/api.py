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

from tmlib.workflow.description import WorkflowDescription
from tmlib.workflow.submission import SubmissionManager
from tmlib.workflow.tmaps.api import WorkflowManager
from tmlib.models import (
    Experiment, ChannelLayer, Plate, Acquisition, Feature, PyramidTileFile,
    Cycle, Well, Site, ChannelImageFile, Channel, IllumstatsFile
)
from tmlib.image import PyramidTile
from tmlib.workflow.metaconfig import SUPPORTED_MICROSCOPE_TYPES
from tmlib.models.plate import SUPPORTED_PLATE_AQUISITION_MODES
from tmserver.util import (
    extract_model_from_path,
    extract_model_from_body
)
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


@api.route('/channel_layers/<channel_layer_id>/tiles', methods=['GET'])
@extract_model_from_path(ChannelLayer)
def get_image_tile(channel_layer):
    """Sends a tile image for a specific layer.
    This route is accessed by openlayers."""
    x = request.args.get('x')
    y = request.args.get('y')
    z = request.args.get('z')
    if not x or not y or not z:
        raise MalformedRequestError()
    else:
        x = int(x)
        y = int(y)
        z = int(z)

    logger.debug(
        'get image tile: x=%d, y=%d, z=%d, zplane=%d, tpoint=%d',
        x, y, z, channel_layer.zplane, channel_layer.tpoint
    )

    tile_file = db.session.query(PyramidTileFile).filter_by(
        column=x, row=y, level=z, channel_layer_id=channel_layer.id
    ).one_or_none()
    if tile_file is None:
        raise ResourceNotFoundError(
            'Tile not found: column=%d, row=%d, level=%d' % (x, y, z)
        )
    return send_file(tile_file.location)
    #     logger.warn('file does not exist - send empty image')
    #     from cStringIO import StringIO
    #     f = StringIO()
    #     img = PyramidTile.create_as_background()
    #     buf = img.array.get_buffer()
    #     f.write(buf.tostring)
    #     f.seek(0)
    #     return send_file(f, mimetype='image/jpeg')


@api.route('/cycles/id', methods=['GET'])
@jwt_required()
def get_cycle_id():
    experiment_name = request.args.get('experiment_name')
    plate_name = request.args.get('plate_name')
    cycle_index = request.args.get('cycle_index')
    cycle = db.session.query(Cycle).\
        join(Plate).\
        join(Experiment).\
        filter(
            Experiment.name == experiment_name,
            Plate.name == plate_name,
            Cycle.index == cycle_index,
        ).\
        one()
    return jsonify({
        'id': encode_pk(cycle.id)
    })


@api.route('/channels/id', methods=['GET'])
@jwt_required()
def get_channel_id():
    experiment_name = request.args.get('experiment_name')
    channel_name = request.args.get('channel_name')
    channel = db.session.query(Channel).\
        join(Experiment).\
        filter(
            Experiment.name == experiment_name,
            Channel.name == channel_name,
        ).\
        one()
    return jsonify({
        'id': encode_pk(channel.id)
    })


@api.route('/cycles/<cycle_id>/image-files', methods=['GET'])
@jwt_required()
@extract_model_from_path(Cycle)
def get_channel_image(cycle):
    channel_name = request.args.get('channel_name')
    well_name = request.args.get('well_name')
    # TODO: raise MissingGETParameterError when arg missing
    x = int(request.args.get('x'))
    y = int(request.args.get('y'))
    tpoint = int(request.args.get('tpoint'))
    zplane = int(request.args.get('zplane'))
    illumcorr = bool(request.args.get('correct'))
    site_id = db.session.query(Site.id).\
        join(Well).\
        filter(
            Well.plate_id == cycle.plate_id, Well.name == well_name,
            Site.x == x, Site.y == y
        ).\
        one()[0]
    channel_id = db.session.query(Channel.id).\
        filter_by(experiment_id=cycle.plate.experiment_id, name=channel_name).\
        one()[0]
    image_file = db.session.query(ChannelImageFile).\
        filter_by(
            cycle_id=cycle.id, site_id=site_id, channel_id=channel_id,
            tpoint=tpoint
        ).\
        one()
    img = image_file.get(zplane)
    if illumcorr:
        # TODO: cache for a limited amount of time to not having to load
        # the file repeatedly when user downloads multiple files
        logger.info('correct image for illumination artefacts')
        illumstats_file = db.session.query(IllumstatsFile).\
            filter_by(channel_id=channel_id, cycle_id=cycle.id).\
            one_or_none()
        if illumstats_file is None:
            raise ValueError('No illumination statistics found.')
        stats = illumstats_file.get()
        img = img.correct(stats)
    img = img.align()
    f = StringIO()
    f.write(cv2.imencode('.png', img.array)[1])
    f.seek(0)
    filename = '%s_%s_x%.3d_y%.3d_z%.3d_t%.3d_%s.png' % (
        cycle.plate.experiment.name, well_name, x, y, zplane, tpoint,
        channel_name
    )
    return send_file(
        f,
        attachment_filename=secure_filename(filename),
        mimetype='image/png',
        as_attachment=True
    )


@api.route('/features', methods=['GET'])
@jwt_required()
@extract_model_from_path(Experiment, check_ownership=True)
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
    experiment_id = request.args.get('experiment_id')
    if not experiment_id:
        raise MalformedRequestError(
            'The GET parameter "experiment_id" is required.')

    features = db.session.query(Feature).filter_by(experiment_id=experiment_id).all()

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
@extract_model_from_path(Experiment)
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
def get_experiment_id():
    """Gets the ID of an experiment given its name.

    Response
    --------
    {
        "data": an experiment ID serialized to json
    }

    """
    experiment_name = request.args.get('experiment_name')
    experiment = db.session.query(Experiment).\
        filter_by(user_id=current_identity.id, name=experiment_name).\
        one()
    return jsonify({
        'id': encode_pk(experiment.id)
    })


@api.route('/experiments/<experiment_id>/workflow/submit', methods=['POST'])
@jwt_required()
@extract_model_from_path(Experiment)
def submit_workflow(experiment):
    logger.info('submit workflow')
    data = json.loads(request.data)
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
@extract_model_from_path(Experiment)
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
@extract_model_from_path(Experiment)
def get_workflow_status(experiment):
    logger.info('get workflow status')
    workflow = gc3pie.retrieve_jobs(experiment, 'workflow')
    status = gc3pie.get_status_of_submitted_jobs(workflow)
    return jsonify({
        'data': status
    })


@api.route('/experiments/<experiment_id>/workflow/load', methods=['GET']) 
@jwt_required()
@extract_model_from_path(Experiment)
def get_workflow_description(experiment):
    logger.info('get workflow description')
    description = experiment.workflow_description
    return jsonify({
        'data': description.as_dict()
    })


@api.route('/experiments/<experiment_id>/workflow/save', methods=['POST'])
@jwt_required()
@extract_model_from_path(Experiment)
def save_workflow_description(experiment):
    data = json.loads(request.data)
    workflow_description = WorkflowDescription(**data['description'])
    experiment.persist_workflow_description(workflow_description)
    return jsonify({
        'message': 'ok'
    })


@api.route('/experiments/<experiment_id>/workflow/kill', methods=['POST']) 
@jwt_required()
@extract_model_from_path(Experiment)
def kill_workflow(experiment):
    data = json.loads(request.data)
    logger.info('kill workflow')
    workflow = gc3pie.retrieve_jobs(experiment, 'workflow')
    gc3pie.kill_jobs(workflow)
    return jsonify({
        'message': 'ok'
    })


@api.route('/experiments/<experiment_id>/workflow/log', methods=['POST']) 
@jwt_required()
@extract_model_from_path(Experiment)
def get_job_log_output(experiment):
    data = json.loads(request.data)
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
def create_experiment():
    data = json.loads(request.data)

    name = data.get('name')
    description = data.get('description', '')
    microscope_type = data.get('microscope_type')
    plate_format = data.get('plate_format')
    plate_acquisition_mode = data.get('plate_acquisition_mode')

    if any([var is None for var in [name, microscope_type, plate_format,
                                    plate_acquisition_mode]]):
        raise MalformedRequestError()

    e = Experiment(
        name=name,
        description=description,
        user_id=current_identity.id,
        microscope_type=microscope_type,
        plate_format=plate_format,
        root_directory=current_app.config['TMAPS_STORAGE_HOME'],
        plate_acquisition_mode=plate_acquisition_mode
    )
    db.session.add(e)
    db.session.commit()

    return jsonify({
        'data': e
    })


@api.route('/experiments/<experiment_id>', methods=['DELETE'])
@jwt_required()
@extract_model_from_path(Experiment, check_ownership=True)
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

    return jsonify(message='Deletion ok')


@api.route('/plates/<plate_id>', methods=['GET'])
@jwt_required()
@extract_model_from_path(Plate, check_ownership=True)
def get_plate(plate):
    return jsonify(data=plate)


@api.route('/plates', methods=['GET'])
@jwt_required()
def get_plates():
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
    experiment_id = request.args.get('experiment_id')
    if not experiment_id:
        raise MissingGETParameterError('experiment_id')
    experiment = db.session.query(Experiment).get_with_hash(experiment_id)
    if not experiment:
        raise ResourceNotFoundError('Experiment')
    if not experiment.belongs_to(current_identity):
        raise NotAuthorizedError()

    return jsonify(data=experiment.plates)


@api.route('/plates/<plate_id>', methods=['DELETE'])
@jwt_required()
@extract_model_from_path(Plate, check_ownership=True)
def delete_plate(plate):
    db.session.delete(plate)
    db.session.commit()
    return jsonify(message='Deletion ok')


@api.route('/plates', methods=['POST'])
@jwt_required()
@extract_model_from_body(Experiment, check_ownership=True)
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
    data = json.loads(request.data)
    name = data.get('name')
    desc = data.get('description', '')
    if not name:
        raise MissingPOSTParameterError('name')
    pl = Plate(
        name=name, description=desc,
        experiment_id=experiment.id
    )
    db.session.add(pl)
    db.session.commit()
    return jsonify(data=pl)


@api.route('/plates/id', methods=['GET'])
@jwt_required()
def get_plate_id():
    experiment_name = request.args.get('experiment_name')
    plate_name = request.args.get('plate_name')
    plate = db.session.query(Plate).\
        join(Experiment).\
        filter(
            Experiment.name == experiment_name,
            Plate.name == plate_name,
        ).\
        one()
    return jsonify({
        'id': encode_pk(plate.id)
    })


@api.route('/acquisitions', methods=['POST'])
@jwt_required()
@extract_model_from_body(Plate, check_ownership=True)
def create_acquisition(plate):
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
    data = json.loads(request.data)
    name = data.get('name')
    desc = data.get('description', '')

    if not name:
        raise MissingPOSTParameterError('name')

    aq = Acquisition(
        name=name, description=desc,
        plate_id=plate.id
    )
    db.session.add(aq)
    db.session.commit()

    return jsonify(data=aq)


@api.route('/acquisitions/<acquisition_id>', methods=['DELETE'])
@jwt_required()
@extract_model_from_path(Acquisition, check_ownership=True)
def delete_acquisition(acquisition):
    db.session.delete(acquisition)
    db.session.commit()
    return jsonify(message='Deletion ok')


@api.route('/acquisitions/<acquisition_id>', methods=['GET'])
@jwt_required()
@extract_model_from_path(Acquisition, check_ownership=True)
def get_acquisition(acquisition):
    return jsonify(data=acquisition)


@api.route('/acquisitions/id', methods=['GET'])
@jwt_required()
def get_acquisition_id():
    experiment_name = request.args.get('experiment_name')
    plate_name = request.args.get('plate_name')
    acquisition_name = request.args.get('acquisition_name')
    acquisition = db.session.query(Acquisition).\
        join(Plate).\
        join(Experiment).\
        filter(
            Experiment.name == experiment_name,
            Plate.name == plate_name,
            Acquisition.name == acquisition_name
        ).\
        one()

    return jsonify({
        'id': encode_pk(acquisition.id)
    })


@api.route('/acquisitions/<acquisition_id>/image_files', methods=['GET'])
@jwt_required()
@extract_model_from_path(Acquisition, check_ownership=True)
def get_acquisition_image_files(acquisition):
    return jsonify({
        'data': acquisition.microscope_image_files
    })


@api.route('/acquisitions/<acquisition_id>/metadata_files', methods=['GET'])
@jwt_required()
@extract_model_from_path(Acquisition, check_ownership=True)
def get_acquisition_metadata_files(acquisition):
    return jsonify({
        'data': acquisition.microscope_metadata_files
    })
