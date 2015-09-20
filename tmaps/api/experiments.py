import json
import os
import os.path as p

from flask import jsonify, request, send_from_directory, send_file
from flask_jwt import jwt_required
from flask.ext.jwt import current_user

import numpy as np

from tmaps.models import Experiment
from tmaps.extensions.encrypt import decode
from tmaps.api import api
import tmaps.posmapper


@api.route('/experiments/<experiment_id>/layers/<layer_name>/<path:filename>', methods=['GET'])
def expdata_file(experiment_id, layer_name, filename):
    """
    Send a tile image for a specific layer.
    This route is accessed by openlayers.

    """
    # TODO: This method should also be flagged with `@jwt_required()`.
    # openlayers needs to send the token along with its request for files s.t.
    # the server can check if the user is authorized to access the experiment
    # with id `experiment_id`.
    is_authorized = True
    # import ipdb; ipdb.set_trace()
    experiment_id = decode(experiment_id)
    if is_authorized:
        filepath = p.join(Experiment.query.get(experiment_id).location,
                          'layers',
                          layer_name,
                          filename)
        return send_file(filepath)
    else:
        return 'You have no permission to access this ressource', 401


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

    where an experiment object looks as follows:

    {
        "id": int,
        "name": string,
        "description": string,
        "owner": string,
        "layers": [
            {
                "name",
                "imageSize": [int, int],
                "pyramidPath": string
            },
            ...
        ]
    }

    """

    experiments_owned = [e.as_dict() for e in current_user.experiments]
    experiments_shared = [e.as_dict()
                          for e in current_user.received_experiments]
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

    where an experiment object looks as follows:

    {
        "id": int,
        "name": string,
        "description": string,
        "owner": string,
        "layers": [
            {
                "name",
                "imageSize": [int, int],
                "pyramidPath": string
            },
            ...
        ]
    }

    """

    experiment_id = decode(experiment_id)

    experiments = current_user.experiments + current_user.received_experiments
    ex = filter(lambda e: e.id == experiment_id, experiments)

    if ex:
        return jsonify(ex[0].as_dict())
    else:
        return 'User does not have an experiment with id %d' % experiment_id, 404


@api.route('/experiments/<experiment_id>/cells', methods=['GET'])
# @jwt_required()
def get_cell_at_pos(experiment_id):
    experiment_id = decode(experiment_id)
    ex = Experiment.query.get(experiment_id)
    if not ex:
        return 'No experiment found', 404

    x = request.args.get('x')
    y = request.args.get('y')
    if x and y:
        x = float(x)
        y = float(y)
        cell_id = posmapper.get_cell_at_pos(ex, x, y)
        return jsonify(cell_id=cell_id)
    else:
        # arr = ex.dataset['/objects/cells/centroids'][()]
        loc = os.path.join(ex.location, 'outlines.json')
        return send_file(loc)
        # ids = map(int, arr[:, 0])
        # xy = arr[:, 1:3].tolist()
        # centroids = dict(zip(ids, xy))

        # return jsonify(centroids)



def _get_feat_property_extractor(prop):
    if prop in ['min', 'max', 'mean', 'median', 'var', 'std']:
        f = getattr(np, prop)
        return lambda mat: f(mat, axis=0)
    elif prop.startswith('perc'):
        p = int(prop[-2:])
        return lambda mat: np.percentile(mat, p, axis=0)
    else:
        raise Exception('No extractor for property: ' + prop)
