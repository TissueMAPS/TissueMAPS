import json
import os.path as p

from flask import jsonify, send_file, current_app, request
from flask.ext.jwt import jwt_required
from flask.ext.jwt import current_identity

import tmlib.workflow.registry
from tmlib.models import Experiment, ChannelLayer, Plate, Acquisition
from tmlib.workflow.canonical import CanonicalWorkflowDescription
from tmlib.workflow.tmaps.api import WorkflowManager

from tmaps.util import get
from tmaps.extensions import db
from tmaps.api import api
from tmaps.error import (
    MalformedRequestError
)


@api.route('/channel_layers/<channel_layer_id>/tiles/<path:filename>', methods=['GET'])
@get(ChannelLayer)
def get_image_tile(channel_layer, filename):
    """Send a tile image for a specific layer.
    This route is accessed by openlayers."""

    filepath = p.join(channel_layer.location, filename)
    return send_file(filepath)


@api.route('/experiments/<experiment_id>/features', methods=['GET'])
@jwt_required()
@get(Experiment, check_ownership=True)
def get_features(experiment):
    """
    Send a list of feature objects.

    Response:

    {
        "features": {
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
    features = {}
    for t in experiment.mapobject_types:
        features[t.name] = [{'name': f.name} for f in t.features]

    return jsonify({
        'features': features
    })


@api.route('/experiments', methods=['GET'])
@jwt_required()
def get_experiments():
    """
    Get all experiments for the current user

    Response:
    {
        "experiments": list of experiment objects,
    }

    """
    return jsonify({
        'experiments': current_identity.experiments
    })


@api.route('/experiments/<experiment_id>', methods=['GET'])
@get(Experiment)
@jwt_required()
def get_experiment(experiment):
    """
    Get an experiment by id.

    Response:
    {
        experiment: an experiment object serialized to json
    }

    """
    return jsonify({
        'experiment': experiment
    })


@api.route('/experiments/<experiment_id>/workflow_description', methods=['GET'])
@get(Experiment)
@jwt_required()
def get_workflow_description(experiment):
    """
    Get the workflow description for this experiment.

    Response:
    {
        workflow_description: a serialized workflow description
    }

    """
    desc = CanonicalWorkflowDescription()
    return jsonify({
        'workflow_description': desc.as_dict()
    })


@api.route('/experiments/<experiment_id>/workflow', methods=['POST'])
@get(Experiment)
@jwt_required()
def submit_workflow(experiment):
    data = json.loads(request.data)
    WorkflowType = tmlib.workflow.registry.get_workflow_description(data['type'])
    wfd = WorkflowType(stages=data['stages'])
    manager = WorkflowManager()
    wf = manager.create_workflow(wfd)
    manager.submit_jobs()

    # TODO: submit
    return jsonify({
        'message': 'ok'
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
        root_directory=current_app.config['TMAPS_STORAGE'],
        plate_acquisition_mode=plate_acquisition_mode
    )
    db.session.add(e)
    db.session.commit()

    return jsonify({
        'experiment': e
    })


@api.route('/experiments/<experiment_id>', methods=['DELETE'])
@jwt_required()
@get(Experiment, check_ownership=True)
def delete_experiment(experiment):
    db.session.delete(experiment)
    db.session.commit()

    return jsonify(message='Deletion ok')


@api.route('/plates/<plate_id>', methods=['GET'])
@jwt_required()
@get(Plate, check_ownership=True)
def get_plate(plate):
    return jsonify(plate=plate)


@api.route('/experiments/<experiment_id>/plates', methods=['GET'])
@jwt_required()
@get(Experiment, check_ownership=True)
def get_plates(experiment):
    return jsonify(plates=experiment.plates)


@api.route('/plates/<plate_id>', methods=['DELETE'])
@jwt_required()
@get(Plate, check_ownership=True)
def delete_plate(plate):
    db.session.delete(plate)
    db.session.commit()

    return jsonify(message='Deletion ok')


@api.route('/experiments/<experiment_id>/plates', methods=['POST'])
@jwt_required()
@get(Experiment, check_ownership=True)
def create_plate(experiment):
    """
    Create a new plate for the experiment with id `experiment_id`.

    Request
    -------

    {
        name: string,
        description: string
    }

    Response
    --------

    Plate object

    """
    data = json.loads(request.data)
    pl_name = data.get('name')
    pl_desc = data.get('description', '')

    if not pl_name:
        raise MalformedRequestError()

    pl = Plate(
        name=pl_name, description=pl_desc,
        experiment_id=experiment.id)
    db.session.add(pl)
    db.session.commit()

    return jsonify(plate=pl)


@api.route('/plates/<plate_id>/acquisitions', methods=['POST'])
@jwt_required()
@get(Plate, check_ownership=True)
def create_acquisition(plate):
    """
    Create a new acquisition for the plate with id `plate_id`.

    Request
    {
        name: string,
        description: string
    }

    Response
    --------

    Acquisition object

    """
    data = json.loads(request.data)
    name = data.get('name')
    desc = data.get('description', '')

    if not name:
        raise MalformedRequestError()

    aq = Acquisition(
        name=name, description=desc,
        plate_id=plate.id)
    db.session.add(aq)
    db.session.commit()

    return jsonify(acquisition=aq)


@api.route('/acquisitions/<acquisition_id>', methods=['DELETE'])
@jwt_required()
@get(Acquisition, check_ownership=True)
def delete_acquisition(acquisition):
    db.session.delete(acquisition)
    db.session.commit()
    return jsonify(message='Deletion ok')


@api.route('/acquisitions/<acquisition_id>', methods=['GET'])
@jwt_required()
@get(Acquisition, check_ownership=True)
def get_acquisition(acquisition):
    return jsonify(acquisition=acquisition)

# @api.route('/experiments/<exp_id>/convert-images', methods=['POST'])
# @jwt_required()
# def convert_images(exp_id):
#     """
#     Performs stage "image_conversion" of the canonical TissueMAPS workflow,
#     consisting of the steps "metaextract", "metaconfig", and "imextract"
#     """
#     # e = Experiment.get(exp_id)
#     # if not e:
#     #     return RESOURCE_NOT_FOUND_RESPONSE
#     # if not e.belongs_to(current_identity):
#     #     return NOT_AUTHORIZED_RESPONSE
#     # # if not e.creation_stage == 'WAITING_FOR_IMAGE_CONVERSION':
#     # #     return 'Experiment not in stage WAITING_FOR_IMAGE_CONVERSION', 400

#     # engine = current_app.extensions['gc3pie'].engine
#     # session = current_app.extensions['gc3pie'].session

#     # data = json.loads(request.data)
#     # metaconfig_args = data['metaconfig']
#     # imextract_args = data['imextract']

#     # exp = e.tmlib_object

#     # workflow_description = tmlib.tmaps.canonical.CanonicalWorkflowDescription()
#     # conversion_stage = tmlib.tmaps.canonical.CanonicalWorkflowStageDescription(
#     #     name='image_conversion')
#     # metaextract_step = tmlib.tmaps.canonical.CanonicalWorkflowStepDescription(
#     #     name='metaextract', args={})
#     # metaconfig_step = tmlib.tmaps.canonical.CanonicalWorkflowStepDescription(
#     #     name='metaconfig', args=metaconfig_args)
#     # imextract_step = tmlib.tmaps.canonical.CanonicalWorkflowStepDescription(
#     #     name='imextract', args=imextract_args)
#     # conversion_stage.add_step(metaextract_step)
#     # conversion_stage.add_step(metaconfig_step)
#     # conversion_stage.add_step(imextract_step)
#     # workflow_description.add_stage(conversion_stage)

#     # # Create tmlib.workflow.Workflow object that can be added to the session
#     # jobs = tmlib.tmaps.workflow.Workflow(exp, verbosity=1, start_stage='image_conversion',
#     #                 description=workflow_description)

#     # # Add the task to the persistent session
#     # e.update(creation_stage='CONVERTING_IMAGES')

#     # # Add the new task to the session
#     # persistent_id = session.add(jobs)

#     # # TODO: Check if necessary
#     # # TODO: Consider session.flush()
#     # session.save_all()

#     # # Add only the new task in the session to the engine
#     # # (all other tasks are already in the engine)
#     # task = session.load(persistent_id)
#     # engine.add(task)

#     # # Create a database entry that links the current user
#     # # to the task and experiment for which this task is executed.
#     # Submission.create(
#     #     submitting_user_id=current_identity.id,
#     #     experiment_id=e.id,
#     #     task_id=persistent_id)

#     # e.update(creation_stage='WAITING_FOR_IMAGE_CONVERSION')

#     # TODO: Return thumbnails
#     return 'Creation ok', 200


# @api.route('/experiments/<exp_id>/rerun-metaconfig', methods=['POST'])
# @jwt_required()
# def rerun_metaconfig(exp_id):
#     """
#     Reruns the step "metaconfig" (and the subsequent step "imextract")
#     of stage "image_conversion" of the canonical TissueMAPS workflow.

#     Note
#     ----
#     This works only if the "metaextract" step was already performed previously
#     and terminated successfully.
#     """
#     e = db.session.query(Experiment).get_with_hash(exp_id)
#     if not e:
#         return RESOURCE_NOT_FOUND_RESPONSE
#     if not e.belongs_to(current_identity):
#         return NOT_AUTHORIZED_RESPONSE
#     # if not e.creation_stage == 'WAITING_FOR_IMAGE_CONVERSION':
#     #     return 'Experiment not in stage WAITING_FOR_IMAGE_CONVERSION', 400

#     engine = current_app.extensions['gc3pie'].engine
#     session = current_app.extensions['gc3pie'].session

#     data = json.loads(request.data)
#     metaextract_args = data['metaextract']
#     metaconfig_args = data['metaconfig']
#     imextract_args = data['imextract']

#     exp = Exp(e.location)
#     workflow_description = CanonicalWorkflowDescription()
#     conversion_stage = CanonicalWorkflowStageDescription(
#                             name='image_conversion')
#     metaextract_step = CanonicalWorkflowStepDescription(
#                             name='metaextract', args=metaextract_args)
#     metaconfig_step = CanonicalWorkflowStepDescription(
#                             name='metaconfig', args=metaconfig_args)
#     imextract_step = CanonicalWorkflowStepDescription(
#                             name='imextract', args=imextract_args)
#     conversion_stage.add_step(metaextract_step)
#     conversion_stage.add_step(metaconfig_step)
#     conversion_stage.add_step(imextract_step)
#     workflow_description.add_stage(conversion_stage)

#     jobs = Workflow(exp, verbosity=1, start_stage='image_conversion',
#                     start_step='metaconfig', description=workflow_description)

#     # Add the task to the persistent session
#     e.update(creation_stage='CONVERTING_IMAGES')

#     # Add the new task to the session
#     persistent_id = session.add(jobs)

#     # Add only the new task in the session to the engine
#     # (all other tasks are already in the engine)
#     for task in session:
#         if task.persistent_id == persistent_id:
#             engine.add(task)

#     # Create a database entry that links the current user
#     # to the task and experiment for which this task is executed.
#     TaskSubmission.create(
#         submitting_user_id=current_identity.id,
#         experiment_id=e.id,
#         task_id=persistent_id)

#     e.update(creation_stage='WAITING_FOR_IMAGE_CONVERSION')

#     return 'Creation ok', 200


# @api.route('/experiments/<exp_id>/create_pyramids', methods=['POST'])
# @jwt_required()
# def create_pyramids(exp_id):
#     """
#     Submits stage "pyramid_creation" of the canonical TissueMAPS workflow,
#     consisting of the "illuminati" step.
#     Optionally submits stage "image_preprocessing", consisting of steps
#     "corilla" and/or "align", prior to the submission of "pyramid_creation"
#     in case the arguments "illumcorr" and/or "align" of the "illuminati" step
#     were set to ``True``.
#     """
#     e = db.session.query(Experiment).get_with_hash(exp_id)
#     if not e:
#         return RESOURCE_NOT_FOUND_RESPONSE
#     if not e.belongs_to(current_identity):
#         return NOT_AUTHORIZED_RESPONSE
#     # if not e.creation_stage == 'WAITING_FOR_IMAGE_CONVERSION':
#     #     return 'Experiment not in stage WAITING_FOR_IMAGE_CONVERSION', 400

#     engine = current_app.extensions['gc3pie'].engine
#     session = current_app.extensions['gc3pie'].session

#     data = json.loads(request.data)
#     illuminati_args = data['illuminati']
#     # NOTE: If the user wants to correct images for illumination artifacts
#     # and/or align images between cycles, the arguments for the "corilla"
#     # and "align" steps have to be provided as well (otherwise empty
#     # objects should be provided)
#     corilla_args = data['corilla']
#     align_args = data['align']

#     workflow_description = tmlib.tmaps.canonical.CanonicalWorkflowDescription()
#     if corilla_args or align_args:
#         preprocessing_stage = CanonicalWorkflowStageDescription(
#                                 name='image_preprocessing')
#         if corilla_args:
#             corilla_step = CanonicalWorkflowStepDescription(
#                                 name='corilla', args=corilla_args)
#             preprocessing_stage.add_step(corilla_step)
#         if align_args:
#             align_step = CanonicalWorkflowStepDescription(
#                                 name='align', args=align_args)
#             preprocessing_stage.add_step(align_step)
#         workflow_description.add_stage(preprocessing_stage)
#     pyramid_creation_stage = CanonicalWorkflowStageDescription(
#                                 name='pyramid_creation')
#     illuminati_step = CanonicalWorkflowStepDescription(
#                                 name='illuminati', args=illuminati_args)
#     pyramid_creation_stage.add_step(illuminati_step)
#     workflow_description.add_stage(pyramid_creation_stage)

#     exp = Exp(e.location)
#     jobs = Workflow(exp, verbosity=1, description=workflow_description)

#     # Add the task to the persistent session
#     e.update(creation_stage='CONVERTING_IMAGES')

#     # Add the new task to the session
#     persistent_id = session.add(jobs)

#     # Add only the new task in the session to the engine
#     # (all other tasks are already in the engine)
#     for task in session:
#         if task.persistent_id == persistent_id:
#             engine.add(task)

#     # Create a database entry that links the current user
#     # to the task and experiment for which this task is executed.
#     TaskSubmission.create(
#         submitting_user_id=current_identity.id,
#         experiment_id=e.id,
#         task_id=persistent_id)

#     e.update(creation_stage='WAITING_FOR_IMAGE_CONVERSION')

#     # TODO: Return thumbnails
#     return 'Creation ok', 200


# @api.route('/experiments/<exp_id>/creation-stage', methods=['PUT'])
# @jwt_required()
# def change_creation_state(exp_id):
#     e = db.session.query(Experiment).get_with_hash(exp_id)
#     if not e:
#         return RESOURCE_NOT_FOUND_RESPONSE
#     if not e.belongs_to(current_identity):
#         return NOT_AUTHORIZED_RESPONSE

#     data = json.loads(request.data)
#     new_stage = data['stage']

#     if new_stage == 'WAITING_FOR_IMAGE_CONVERSION' and e.is_ready_for_image_conversion:
#         e.update(creation_stage='WAITING_FOR_IMAGE_CONVERSION')
#         return 'Stage changed', 200
#     elif new_stage == 'WAITING_FOR_UPLOAD':
#         e.update(creation_stage='WAITING_FOR_UPLOAD')
#         return 'Stage changed', 200
#     # TODO: Check that all plates have been created, only then allow changing states
#     elif new_stage == 'WAITING_FOR_PYRAMID_CREATION':
#         e.update(creation_stage='WAITING_FOR_PYRAMID_CREATION')
#         return 'Stage changed', 200
#     else:
#         return 'Stage change impossible', 400
