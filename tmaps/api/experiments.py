import json
import os
import os.path as p

from flask import jsonify, request, send_from_directory, send_file, current_app
from flask.ext.jwt import jwt_required
from flask.ext.jwt import current_identity

import numpy as np

from tmaps.models import Experiment
from tmaps.extensions.encrypt import decode
from tmaps.api import api
from tmaps.api.responses import (
    MALFORMED_REQUEST_RESPONSE,
    RESOURCE_NOT_FOUND_RESPONSE,
    NOT_AUTHORIZED_RESPONSE
)


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

    experiment_id = decode(experiment_id)
    exp = Experiment.query.get(experiment_id)
    dataset = exp.dataset
    features = []

    props = []
    if 'include' in request.args:
        props = request.args.get('include').split(',')
        print props

    features = []

    dset = dataset['/objects/cells/features']
    feat_names = dset.attrs['names'].tolist()
    feat_objs = [{'name': f} for f in feat_names]

    mat = dset[()]
    for prop in props:
        f = _get_feat_property_extractor(prop)
        prop_values = f(mat)
        for feat, val in zip(feat_objs, prop_values):
            feat[prop] = val

        features += feat_objs

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
    e = Experiment.get(exp_id)
    if not e:
        return RESOURCE_NOT_FOUND_RESPONSE
    if not e.belongs_to(current_identity):
        return NOT_AUTHORIZED_RESPONSE
    if not e.creation_stage == 'WAITING_FOR_IMAGE_CONVERSION':
        return 'Experiment not in stage WAITING_FOR_IMAGE_CONVERSION', 400

    e.update(creation_stage='CONVERTING_IMAGES')

    # TODO: Check that data has the correct structure
    data = json.loads(request.data)
    metaconfig_args = data['metaconfig']
    imextract_args = data['imextract']

    engine = current_app.extensions['gc3pie'].engine
    # TODO: Start conversion

    e.update(creation_stage='WAITING_FOR_IMAGE_CONVERSION')

    # TODO: Return thumbnails
    return 'Creation ok', 200


@api.route('/experiments/<experiment_id>/cells', methods=['GET'])
@jwt_required()
def get_cells(experiment_id):
    ex = Experiment.get(experiment_id)
    if not ex:
        return RESOURCE_NOT_FOUND_RESPONSE

    loc = os.path.join(ex.location, 'outlines.json')
    return send_file(loc)


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
