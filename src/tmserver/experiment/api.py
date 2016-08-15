import json
import os
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

from tmserver.util import decode_url_ids, decode_body_ids, assert_request_params
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

logger = logging.getLogger(__name__)

def _raise_error_when_missing(arg):
    raise MissingGETParameterError(arg)

@api.route(
    '/experiments/<experiment_id>/channel_layers/<channel_layer_id>/tiles',
    methods=['GET']
)
@assert_request_params('x', 'y', 'z')
@decode_url_ids()
def get_image_tile(experiment_id, channel_layer_id):
    """Sends a tile image for a specific layer.
    This route is accessed by openlayers."""
    x = request.args.get('x', type=int)
    y = request.args.get('y', type=int)
    z = request.args.get('z', type=int)

    with tm.utils.ExperimentSession(experiment_id) as session:
        channel_layer = session.query(tm.ChannelLayer).get(channel_layer_id)
        logger.debug(
            'get image tile: x=%d, y=%d, z=%d, zplane=%d, tpoint=%d',
            x, y, z, channel_layer.zplane, channel_layer.tpoint
        )

        tile_file = session.query(tm.PyramidTileFile).\
            filter_by(
                column=x, row=y, level=z,
                channel_layer_id=channel_layer.id
            ).\
            one_or_none()

        if tile_file is None:
            # raise ResourceNotFoundError(
            #     'Tile not found: column=%d, row=%d, level=%d' % (x, y, z)
            # )
            logger.warn('file does not exist - send empty tile')
            f = StringIO()
            tile = PyramidTile.create_as_background()
            f.write(tile.jpeg_encode())
            f.seek(0)
            return send_file(f, mimetype='image/jpeg')
        else:
            return send_file(tile_file.location)


@api.route('/experiments/<experiment_id>/cycles/id', methods=['GET'])
@jwt_required()
@assert_request_params('plate_name', 'cycle_index')
@decode_url_ids()
def get_cycle_id(experiment_id):
    experiment_name = experiment.name
    plate_name = request.args.get('plate_name')
    cycle_index = request.args.get('cycle_index', type=int)
    with tm.utils.ExperimentSession(experiment_id) as session:
        cycle = session.query(tm.Cycle).\
            join(tm.Plate).\
            filter(
                tm.Plate.name == plate_name,
                tm.Cycle.index == cycle_index,
            ).\
            one()
        return jsonify({
            'id': encode_pk(cycle.id)
        })


@api.route('/experiments/<experiment_id>/channels', methods=['GET'])
@jwt_required()
@decode_url_ids()
def get_channels(experiment_id):
    with tm.utils.ExperimentSession(experiment_id) as session:
        channels = session.query(tm.Channel).all()
        return jsonify(data=channels)


@api.route('/experiments/<experiment_id>/mapobject_types', methods=['GET'])
@jwt_required()
@decode_url_ids()
def get_mapobject_types(experiment_id):
    with tm.utils.ExperimentSession(experiment_id) as session:
        mapobject_types = session.query(tm.MapobjectType).all()
        return jsonify(data=mapobject_types)


@api.route('/experiments/<experiment_id>/channels/id', methods=['GET'])
@jwt_required()
@assert_request_params('channel_name')
@decode_url_ids()
def get_channel_id(experiment_id):
    channel_name = request.args.get('channel_name')
    with tm.utils.ExperimentSession(experiment_id) as session:
        channel = session.query(tm.Channel).\
            filter_by(name=channel_name).\
            one()
        return jsonify({
            'id': encode_pk(channel.id)
        })


@api.route('/experiments/<experiment_id>/channel_layers/id', methods=['GET'])
@jwt_required()
@assert_request_params('channel_name', 'tpoint', 'zplane')
@decode_url_ids()
def get_channel_layer_id(experiment_id):
    channel_name = request.args.get('channel_name')
    tpoint = request.args.get('tpoint', type=int)
    zplane = request.args.get('zplane', type=int)
    with tm.utils.ExperimentSession(experiment_id) as session:
        channel_layer = session.query(tm.ChannelLayer).\
            join(tm.Channel).\
            filter(
                tm.Channel.name == channel_name,
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
@assert_request_params(
    'plate_name', 'cycle_index', 'well_name', 'x', 'y', 'tpoint', 'zplane'
)
@decode_url_ids()
def get_channel_image(experiment_id, channel_name):
    plate_name = request.args.get('plate_name')
    well_name = request.args.get('well_name')
    x = request.args.get('x', type=int)
    y = request.args.get('y', type=int)
    cycle_index = request.args.get('cycle_index', type=int)
    tpoint = request.args.get('tpoint', type=int)
    zplane = request.args.get('zplane', type=int)
    illumcorr = request.args.get('correct', type=bool)
    with tm.utils.ExperimentSession(experiment_id) as session:
        site_id = session.query(tm.Site.id).\
            join(tm.Well).\
            join(tm.Plate).\
            filter(
                tm.Plate.name == plate_name,
                tm.Well.name == well_name,
                tm.Site.x == x, tm.Site.y == y
            ).\
            one()[0]
        channel_id = session.query(tm.Channel.id).\
            filter_by(name=channel_name).\
            one()[0]
        image_file = session.query(tm.ChannelImageFile).\
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
            # TODO: cache in Redis for a limited amount of time to not having to
            # load the file repeatedly when user downloads multiple files of the
            # same channel
            logger.info('correct image for illumination artefacts')
            illumstats_file = session.query(tm.IllumstatsFile).\
                filter_by(channel_id=channel_id, cycle_id=image_file.cycle_id).\
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
    f.write(img.encode('png'))
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
    with tm.utils.MainSession() as session:
        experiments = session.query(tm.ExperimentReference).\
            filter_by(user_id=current_identity.id).\
            all()
        return jsonify({
            'data': experiments
        })


@api.route('/experiments/<experiment_id>', methods=['GET'])
@jwt_required()
@decode_url_ids()
def get_experiment(experiment_id):
    """Gets an experiment by id.

    Response
    --------
    {
        "data": an experiment object serialized to json
    }

    """
    logger.info('get experiment #%d', experiment_id)
    with tm.utils.MainSession() as session:
        experiment = session.query(tm.ExperimentReference).get(experiment_id)
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
    with tm.utils.MainSession() as session:
        experiment = session.query(tm.Experiment).\
            filter_by(user_id=current_identity.id, name=experiment_name).\
            one()
        return jsonify({
            'id': encode_pk(experiment.id)
        })


@api.route('/experiments/<experiment_id>/workflow/submit', methods=['POST'])
@jwt_required()
@assert_request_params('description')
@decode_url_ids()
def submit_workflow(experiment_id):
    logger.info('submit workflow')
    data = request.get_json()
    # data = json.loads(request.data)
    workflow_description = WorkflowDescription(**data['description'])
    with tm.utils.MainSession() as session:
        experiment = session.query(tm.ExperimentReference).get(experiment_id)
        experiment.persist_workflow_description(workflow_description)
    workflow_manager = WorkflowManager(experiment_id, 1)
    submission_manager = SubmissionManager(experiment_id, 'workflow')
    submission_id, user_name = submission_manager.register_submission()
    workflow = workflow_manager.create_workflow(
        submission_id, user_name, workflow_description
    )
    gc3pie.store_jobs(workflow)
    gc3pie.submit_jobs(workflow)

    return jsonify({
        'message': 'ok',
        'submission_id': workflow.submission_id
    })


@api.route('/experiments/<experiment_id>/workflow/resubmit', methods=['POST'])
@jwt_required()
@assert_request_params('description')
@decode_url_ids()
def resubmit_workflow(experiment_id):
    logger.info('resubmit workflow')
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


@api.route('/experiments/<experiment_id>/workflow/status', methods=['GET']) 
@jwt_required()
@decode_url_ids()
def get_workflow_status(experiment_id):
    logger.info('get workflow status')
    workflow = gc3pie.retrieve_jobs(experiment_id, 'workflow')
    status = gc3pie.get_status_of_submitted_jobs(workflow)
    return jsonify({
        'data': status
    })


@api.route('/experiments/<experiment_id>/workflow/description', methods=['GET']) 
@jwt_required()
@decode_url_ids()
def get_workflow_description(experiment_id):
    logger.info('get workflow description')
    with tm.utils.MainSession() as session:
        experiment = session.query(tm.ExperimentReference).get(experiment_id)
        description = experiment.workflow_description
    return jsonify({
        'data': description.as_dict()
    })


@api.route('/experiments/<experiment_id>/workflow/description', methods=['POST'])
@jwt_required()
@assert_request_params('description')
@decode_url_ids()
def save_workflow_description(experiment_id):
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
@decode_url_ids()
def kill_workflow(experiment_id):
    logger.info('kill workflow')
    workflow = gc3pie.retrieve_jobs(experiment_id, 'workflow')
    gc3pie.kill_jobs(workflow)
    return jsonify({
        'message': 'ok'
    })


@api.route('/experiments/<experiment_id>/workflow/log', methods=['POST'])
@jwt_required()
@assert_request_params('id')
@decode_url_ids()
def get_job_log_output(experiment_id):
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
    'name', 'microscope_type', 'plate_format', 'plate_acquisition_mode'
)
def create_experiment():
    data = request.get_json()
    name = data.get('name')
    microscope_type = data.get('microscope_type')
    plate_format = int(data.get('plate_format'))
    plate_acquisition_mode = data.get('plate_acquisition_mode')
    description = data.get('description', '')
    with tm.utils.MainSession() as session:
        experiment_ref = tm.ExperimentReference(
            name=name,
            description=description,
            user_id=current_identity.id,
            root_directory=current_app.config['TMAPS_STORAGE_HOME']
        )
        session.add(experiment_ref)
        session.commit()
        experiment_id = experiment_ref.id
        root_directory = experiment_ref.location

    with tm.utils.ExperimentSession(experiment_id) as exp_session:
        experiment = tm.Experiment(
            root_directory=root_directory,
            microscope_type=microscope_type,
            plate_format=plate_format,
            plate_acquisition_mode=plate_acquisition_mode
        )
        exp_session.add(experiment)

    return jsonify({
        'data': {
            'id': experiment_id,
            'name': name,
            'description': description,
            'user': current_identity.name
        }
    })



@api.route('/experiments/<experiment_id>', methods=['DELETE'])
@jwt_required()
@decode_url_ids()
def delete_experiment(experiment_id):
    """Delete an experiment for the current user.

    Response
    --------
    {
        "message": 'Deletion ok'
    }

    """
    with tm.utils.MainSession() as session:
        session.query(tm.ExperimentReference).\
            filter_by(id=experiment_id).\
            delete()
    return jsonify(message='ok')


@api.route('/experiments/<experiment_id>/plates/<plate_id>', methods=['GET'])
@jwt_required()
@decode_url_ids()
def get_plate(experiment_id, plate_id):
    with tm.utils.ExperimentSession(experiment_id) as session:
        plate = session.query(tm.Plate).get(plate_id)
        return jsonify(data=plate)


@api.route('/experiments/<experiment_id>/plates', methods=['GET'])
@jwt_required()
@decode_url_ids()
def get_plates(experiment_id):
    with tm.utils.ExperimentSession(experiment_id) as session:
        plates = session.query(tm.Plate).all()
        return jsonify(data=plates)


@api.route('/experiments/<experiment_id>/plates/<plate_id>', methods=['DELETE'])
@jwt_required()
@decode_url_ids()
def delete_plate(experiment_id, plate_id):
    with tm.utils.ExperimentSession(experiment_id) as session:
        session.query(tm.Plate).filter_by(id=plate_id).delete()
    return jsonify(message='ok')


@api.route('/experiments/<experiment_id>/plates', methods=['POST'])
@jwt_required()
@assert_request_params('name')
@decode_url_ids()
def create_plate(experiment_id):
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

    with tm.utils.ExperimentSession(experiment_id) as session:
        plate = tm.Plate(name=name, description=desc)
        session.add(plate)
        session.commit()

        return jsonify({
            'data': plate,
            'experiment_id': experiment_id
        })

@api.route('/experiments/<experiment_id>/plates/id', methods=['GET'])
@jwt_required()
@assert_request_params('plate_name')
@decode_url_ids()
def get_plate_id(experiment_id):
    plate_name = request.args.get('plate_name')
    with tm.utils.ExperimentSession(experiment_id) as session:
        plate = session.query(tm.Plate).\
            filter_by(name=plate_name).\
            one()
        return jsonify({
            'id': encode_pk(plate.id)
        })


@api.route('/experiments/<experiment_id>/acquisitions', methods=['POST'])
@jwt_required()
@assert_request_params('plate_name', 'name')
@decode_url_ids()
@decode_body_ids()
def create_acquisition(experiment_id):
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
    with tm.utils.ExperimentSession(experiment_id) as session:
        plate = session.query(tm.Plate).\
            filter_by(name=plate_name).\
            one_or_none()
        if plate is None:
            raise ResourceNotFoundError('Plate "%s" not found' % plate_name)
        acquisition = tm.Acquisition(
            name=name, description=desc,
            plate_id=plate.id
        )
        session.add(acquisition)
        session.commit()
        return jsonify(data=acquisition)


@api.route(
    '/experiments/<experiment_id>/acquisitions/<acquisition_id>',
    methods=['DELETE']
)
@jwt_required()
@decode_body_ids()
def delete_acquisition(experiment_id, acquisition_id):
    with tm.utils.ExperimentSession(experiment_id) as session:
        session.query(tm.Acquisition).filter_by(id=acquisition_id).delete()
    return jsonify(message='ok')


@api.route(
    '/experiments/<experiment_id>/acquisitions/<acquisition_id>',
    methods=['GET']
)
@jwt_required()
@decode_url_ids()
def get_acquisition(experiment_id, acquisition_id):
    with tm.utils.ExperimentSession(experiment_id) as session:
        acquisition = session.query(tm.Acquisition).get(acquisition_id)
        return jsonify(data=acquisition)


@api.route('/experiments/<experiment_id>/acquisitions/id', methods=['GET'])
@jwt_required()
@assert_request_params('plate_name', 'acquisition_name')
@decode_body_ids()
def get_acquisition_id(experiment_id):
    plate_name = request.args.get('plate_name')
    acquisition_name = request.args.get('acquisition_name')
    with tm.utils.ExperimentSession(experiment_id) as session:
        acquisition = session.query(tm.Acquisition).\
            join(Plate).\
            filter(
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
@decode_url_ids()
def get_acquisition_image_files(experiment_id, acquisition_id):
    with tm.utils.ExperimentSession(experiment_id) as session:
        acquisition = session.query(tm.Acquisition).get(acquisition_id)
        return jsonify({
            'data': acquisition.microscope_image_files
        })


@api.route(
    '/experiments/<experiment_id>/acquisitions/<acquisition_id>/metadata-files',
    methods=['GET']
)
@jwt_required()
@decode_url_ids()
def get_acquisition_metadata_files(experiment_id, acquisition_id):
    with tm.utils.ExperimentSession(experiment_id) as session:
        acquisition = session.query(tm.Acquisition).get(acquisition_id)
        return jsonify({
            'data': acquisition.microscope_metadata_files
        })
