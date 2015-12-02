import json
import os
import os.path as p

from flask import jsonify, request, send_file, current_app
from flask.ext.jwt import jwt_required
from flask.ext.jwt import current_identity

import numpy as np

import tmlib.experiment
import tmlib.tmaps.workflow
import tmlib.logging_utils
import tmlib.tmaps.canonical
from tmlib.readers import DatasetReader

from tmaps.models import Experiment, TaskSubmission
from tmaps.extensions.encrypt import decode
from tmaps.api import api
from tmaps.api.responses import (
    MALFORMED_REQUEST_RESPONSE,
    RESOURCE_NOT_FOUND_RESPONSE,
    NOT_AUTHORIZED_RESPONSE
)

import logging

# configure tmlib loggers
tmlib_logger = tmlib.logging_utils.configure_logging(logging.INFO)


@api.route('/experiments/<experiment_id>/layers/<layer_name>/<path:filename>', methods=['GET'])
def expdata_file(experiment_id, layer_name, filename):
    """Send a tile image for a specific layer.
    This route is accessed by openlayers."""
    # TODO: This method should also be flagged with `@jwt_required()`.
    # openlayers needs to send the token along with its request for files s.t.
    # the server can check if the user is authorized to access the experiment
    # with id `experiment_id`.
    # import ipdb; ipdb.set_trace()
    e = Experiment.get(experiment_id)
    is_authorized = True
    if is_authorized:
        filepath = p.join(e.location, 'layers', layer_name, filename)
        return send_file(filepath)
    else:
        return NOT_AUTHORIZED_RESPONSE


# TODO: Make auth required. tools subapp should receive token
@api.route('/experiments/<experiment_id>/features', methods=['GET'])
# @jwt_required()
def get_features(experiment_id):
    """
    Send a list of feature objects. In addition to the name and the channel
    to which each feature belongs, the caller may request additional properties
    by listing those as query parameters:

    /experiments/<expid>/features?include=prop1,prop2,...

    where available properties are:

        min, max, mean, median,
        percXX (e.g. perc25 for the 25% percentile),
        var, std

    Response:

    {
        "features": [
            {
                "name": string (the feature's name),
                // additional properties:
                "min": float,
                ....
            }
        ]
    }
    """

    exp = Experiment.get(experiment_id)
    features = []

    props = []
    if 'include' in request.args:
        props = request.args.get('include').split(',')
        print props

    features = []

    # with DatasetReader(exp.dataset_path) as dataset:
    #     dset = dataset.read('/objects/cells/features')
    #     feat_names = dataset.get_attribute('/objects/cells/features', 'names')
    # feat_objs = [{'name': f} for f in feat_names]

    # for prop in props:
    #     f = _get_feat_property_extractor(prop)
    #     prop_values = f(dset)
    #     for feat, val in zip(feat_objs, prop_values):
    #         feat[prop] = val

    #     features += feat_objs

    return jsonify(features=features)


@api.route('/experiments', methods=['GET'])
@jwt_required()
def get_experiments():
    """
    Get all experiments for the current user

    Response:
    {
        "owned": list of experiment objects,
        "shared": list of experiment objects
    }

    where an experiment object is a dict as returned by
    Experiment.as_dict().

    """
    experiments_owned = [e.as_dict() for e in current_identity.experiments]
    experiments_shared = [e.as_dict()
                          for e in current_identity.received_experiments]
    return jsonify({
        'owned': experiments_owned,
        'shared': experiments_shared
    })


@api.route('/experiments/<experiment_id>', methods=['GET'])
@jwt_required()
def get_experiment(experiment_id):
    """
    Get an experiment by id.

    Response:
    {
        an experiment object serialized to json
    }

    where an experiment object is a dict as returned by
    Experiment.as_dict().

    """

    e = Experiment.get(experiment_id)
    if not e:
        return RESOURCE_NOT_FOUND_RESPONSE
    if not e.belongs_to(current_identity):
        return NOT_AUTHORIZED_RESPONSE
    return jsonify(e.as_dict())


def _get_feat_property_extractor(prop):
    if prop in ['min', 'max', 'mean', 'median', 'var', 'std']:
        f = getattr(np, prop)
        return lambda mat: f(mat, axis=0)
    elif prop.startswith('perc'):
        p = int(prop[-2:])
        return lambda mat: np.percentile(mat, p, axis=0)
    else:
        raise Exception('No extractor for property: ' + prop)


@api.route('/experiments', methods=['POST'])
@jwt_required()
def create_experiment():
    data = json.loads(request.data)

    name = data.get('name')
    description = data.get('description', '')
    microscope_type = data.get('microscope_type')
    plate_format = data.get('plate_format')

    if any([var is None for var in [name, microscope_type, plate_format]]):
        return MALFORMED_REQUEST_RESPONSE

    exp = Experiment.create(
        name=name,
        description=description,
        owner=current_identity,
        microscope_type=microscope_type,
        plate_format=plate_format
    )

    return jsonify(exp.as_dict())


@api.route('/experiments/<experiment_id>', methods=['DELETE'])
@jwt_required()
def delete_experiment(experiment_id):
    e = Experiment.get(experiment_id)
    if not e:
        return RESOURCE_NOT_FOUND_RESPONSE
    if not e.belongs_to(current_identity):
        return NOT_AUTHORIZED_RESPONSE

    e.delete()
    return 'Deletion ok', 200


@api.route('/experiments/<exp_id>/convert-images', methods=['POST'])
@jwt_required()
def convert_images(exp_id):
    """
    Performs stage "image_conversion" of the canonical TissueMAPS workflow,
    consisting of the steps "metaextract", "metaconfig", and "imextract"
    """
    e = Experiment.get(exp_id)
    if not e:
        return RESOURCE_NOT_FOUND_RESPONSE
    if not e.belongs_to(current_identity):
        return NOT_AUTHORIZED_RESPONSE
    # if not e.creation_stage == 'WAITING_FOR_IMAGE_CONVERSION':
    #     return 'Experiment not in stage WAITING_FOR_IMAGE_CONVERSION', 400

    engine = current_app.extensions['gc3pie'].engine
    session = current_app.extensions['gc3pie'].session

    data = json.loads(request.data)
    metaconfig_args = data['metaconfig']
    imextract_args = data['imextract']

    exp = e.tmlib_object

    workflow_description = tmlib.tmaps.canonical.CanonicalWorkflowDescription()
    conversion_stage = tmlib.tmaps.canonical.CanonicalWorkflowStageDescription(
        name='image_conversion')
    metaextract_step = tmlib.tmaps.canonical.CanonicalWorkflowStepDescription(
        name='metaextract', args={})
    metaconfig_step = tmlib.tmaps.canonical.CanonicalWorkflowStepDescription(
        name='metaconfig', args=metaconfig_args)
    imextract_step = tmlib.tmaps.canonical.CanonicalWorkflowStepDescription(
        name='imextract', args=imextract_args)
    conversion_stage.add_step(metaextract_step)
    conversion_stage.add_step(metaconfig_step)
    conversion_stage.add_step(imextract_step)
    workflow_description.add_stage(conversion_stage)

    # Create tmlib.workflow.Workflow object that can be added to the session
    jobs = tmlib.tmaps.workflow.Workflow(exp, verbosity=1, start_stage='image_conversion',
                    description=workflow_description)

    # Add the task to the persistent session
    e.update(creation_stage='CONVERTING_IMAGES')

    # Add the new task to the session
    persistent_id = session.add(jobs)

    # TODO: Check if necessary
    # TODO: Consider session.flush()
    session.save_all()

    # Add only the new task in the session to the engine
    # (all other tasks are already in the engine)
    task = session.load(persistent_id)
    engine.add(task)

    # Create a database entry that links the current user
    # to the task and experiment for which this task is executed.
    TaskSubmission.create(
        submitting_user_id=current_identity.id,
        experiment_id=e.id,
        task_id=persistent_id)

    e.update(creation_stage='WAITING_FOR_IMAGE_CONVERSION')

    # TODO: Return thumbnails
    return 'Creation ok', 200


@api.route('/experiments/<exp_id>/rerun-metaconfig', methods=['POST'])
@jwt_required()
def rerun_metaconfig(exp_id):
    """
    Reruns the step "metaconfig" (and the subsequent step "imextract")
    of stage "image_conversion" of the canonical TissueMAPS workflow.

    Note
    ----
    This works only if the "metaextract" step was already performed previously
    and terminated successfully.
    """
    e = Experiment.get(exp_id)
    if not e:
        return RESOURCE_NOT_FOUND_RESPONSE
    if not e.belongs_to(current_identity):
        return NOT_AUTHORIZED_RESPONSE
    # if not e.creation_stage == 'WAITING_FOR_IMAGE_CONVERSION':
    #     return 'Experiment not in stage WAITING_FOR_IMAGE_CONVERSION', 400

    engine = current_app.extensions['gc3pie'].engine
    session = current_app.extensions['gc3pie'].session

    data = json.loads(request.data)
    metaextract_args = data['metaextract']
    metaconfig_args = data['metaconfig']
    imextract_args = data['imextract']

    exp = Exp(e.location)
    workflow_description = CanonicalWorkflowDescription()
    conversion_stage = CanonicalWorkflowStageDescription(
                            name='image_conversion')
    metaextract_step = CanonicalWorkflowStepDescription(
                            name='metaextract', args=metaextract_args)
    metaconfig_step = CanonicalWorkflowStepDescription(
                            name='metaconfig', args=metaconfig_args)
    imextract_step = CanonicalWorkflowStepDescription(
                            name='imextract', args=imextract_args)
    conversion_stage.add_step(metaextract_step)
    conversion_stage.add_step(metaconfig_step)
    conversion_stage.add_step(imextract_step)
    workflow_description.add_stage(conversion_stage)

    jobs = Workflow(exp, verbosity=1, start_stage='image_conversion',
                    start_step='metaconfig', description=workflow_description)

    # Add the task to the persistent session
    e.update(creation_stage='CONVERTING_IMAGES')

    # Add the new task to the session
    persistent_id = session.add(jobs)

    # Add only the new task in the session to the engine
    # (all other tasks are already in the engine)
    for task in session:
        if task.persistent_id == persistent_id:
            engine.add(task)

    # Create a database entry that links the current user
    # to the task and experiment for which this task is executed.
    TaskSubmission.create(
        submitting_user_id=current_identity.id,
        experiment_id=e.id,
        task_id=persistent_id)

    e.update(creation_stage='WAITING_FOR_IMAGE_CONVERSION')

    return 'Creation ok', 200


@api.route('/experiments/<exp_id>/create_pyramids', methods=['POST'])
@jwt_required()
def create_pyramids(exp_id):
    """
    Submits stage "pyramid_creation" of the canonical TissueMAPS workflow,
    consisting of the "illuminati" step.
    Optionally submits stage "image_preprocessing", consisting of steps
    "corilla" and/or "align", prior to the submission of "pyramid_creation"
    in case the arguments "illumcorr" and/or "align" of the "illuminati" step
    were set to ``True``.
    """
    e = Experiment.get(exp_id)
    if not e:
        return RESOURCE_NOT_FOUND_RESPONSE
    if not e.belongs_to(current_identity):
        return NOT_AUTHORIZED_RESPONSE
    # if not e.creation_stage == 'WAITING_FOR_IMAGE_CONVERSION':
    #     return 'Experiment not in stage WAITING_FOR_IMAGE_CONVERSION', 400

    engine = current_app.extensions['gc3pie'].engine
    session = current_app.extensions['gc3pie'].session

    data = json.loads(request.data)
    illuminati_args = data['illuminati']
    # NOTE: If the user wants to correct images for illumination artifacts
    # and/or align images between cycles, the arguments for the "corilla"
    # and "align" steps have to be provided as well (otherwise empty
    # objects should be provided)
    corilla_args = data['corilla']
    align_args = data['align']

    workflow_description = tmlib.tmaps.canonical.CanonicalWorkflowDescription()
    if corilla_args or align_args:
        preprocessing_stage = CanonicalWorkflowStageDescription(
                                name='image_preprocessing')
        if corilla_args:
            corilla_step = CanonicalWorkflowStepDescription(
                                name='corilla', args=corilla_args)
            preprocessing_stage.add_step(corilla_step)
        if align_args:
            align_step = CanonicalWorkflowStepDescription(
                                name='align', args=align_args)
            preprocessing_stage.add_step(align_step)
        workflow_description.add_stage(preprocessing_stage)
    pyramid_creation_stage = CanonicalWorkflowStageDescription(
                                name='pyramid_creation')
    illuminati_step = CanonicalWorkflowStepDescription(
                                name='illuminati', args=illuminati_args)
    pyramid_creation_stage.add_step(illuminati_step)
    workflow_description.add_stage(pyramid_creation_stage)

    exp = Exp(e.location)
    jobs = Workflow(exp, verbosity=1, description=workflow_description)

    # Add the task to the persistent session
    e.update(creation_stage='CONVERTING_IMAGES')

    # Add the new task to the session
    persistent_id = session.add(jobs)

    # Add only the new task in the session to the engine
    # (all other tasks are already in the engine)
    for task in session:
        if task.persistent_id == persistent_id:
            engine.add(task)

    # Create a database entry that links the current user
    # to the task and experiment for which this task is executed.
    TaskSubmission.create(
        submitting_user_id=current_identity.id,
        experiment_id=e.id,
        task_id=persistent_id)

    e.update(creation_stage='WAITING_FOR_IMAGE_CONVERSION')

    # TODO: Return thumbnails
    return 'Creation ok', 200


@api.route('/experiments/<experiment_id>/objects', methods=['GET'])
@jwt_required()
def get_objects(experiment_id):
    """
    The response will be built depending on whether the GET arguments
    ?types or ?objects are given.

    Response:
    
    Either

    {
        types: ['cell', 'nucleus']
    }

    or

    {
        objects: {
            1: [[x1, y1], [x2, y2], ....],
            2: [[x1, y1], [x2, y2], ....],
            ...
        }
    }

    or both responses merged into one.

    """
    ex = Experiment.get(experiment_id)
    if not ex:
        return RESOURCE_NOT_FOUND_RESPONSE

    if not ex.belongs_to(current_identity):
        return NOT_AUTHORIZED_RESPONSE

    response = {}

    if 'types' in request.args:
        with ex.dataset as data:
            response['types'] = data['/objects'].keys()
    if 'objects' in request.args:
        with ex.dataset as data:
            objects = {}
            types = data['/objects'].keys()
            for t in types:
                objects[t] = {}
                object_data = data['/objects/%s' % t]
                object_ids = object_data.keys()
                for id in object_ids:
                    objects[t][id] = object_data[id][()].tolist()
            response['objects'] = objects

    return jsonify(response)


@api.route('/experiments/<exp_id>/creation-stage', methods=['PUT'])
@jwt_required()
def change_creation_state(exp_id):
    e = Experiment.get(exp_id)
    if not e:
        return RESOURCE_NOT_FOUND_RESPONSE
    if not e.belongs_to(current_identity):
        return NOT_AUTHORIZED_RESPONSE

    data = json.loads(request.data)
    new_stage = data['stage']

    if new_stage == 'WAITING_FOR_IMAGE_CONVERSION' and e.is_ready_for_image_conversion:
        e.update(creation_stage='WAITING_FOR_IMAGE_CONVERSION')
        return 'Stage changed', 200
    elif new_stage == 'WAITING_FOR_UPLOAD':
        e.update(creation_stage='WAITING_FOR_UPLOAD')
        return 'Stage changed', 200
    # TODO: Check that all plates have been created, only then allow changing states
    elif new_stage == 'WAITING_FOR_PYRAMID_CREATION':
        e.update(creation_stage='WAITING_FOR_PYRAMID_CREATION')
        return 'Stage changed', 200
    else:
        return 'Stage change impossible', 400
