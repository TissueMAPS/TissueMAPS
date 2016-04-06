import os.path as p
import json

from flask.ext.jwt import jwt_required
from flask.ext.jwt import current_identity
from flask.ext.jwt import jwt_required
from flask import jsonify, request
from sqlalchemy.sql import text

from tmaps.api import api
from tmaps.extensions import db

from tmaps.mapobject import MapobjectOutline, MapobjectType
from tmaps.experiment import Experiment
from tmaps.response import (
    MALFORMED_REQUEST_RESPONSE,
    RESOURCE_NOT_FOUND_RESPONSE,
    NOT_AUTHORIZED_RESPONSE
)




def _create_mapobject_feature(obj_id, geometry_obj):
    """Create a GeoJSON feature object given a object id of type int
    and a object that represents a GeoJSON geometry definition."""
    return {
        "type": "Feature",
        "geometry": geometry_obj,
        "properties": {
            "id": str(obj_id)
        }
    }


@api.route('/experiments/<experiment_id>/mapobjects/<object_name>', methods=['GET'])
def get_mapobjects_tile(experiment_id, object_name):

    ex = db.session.query(Experiment).get_with_hash(experiment_id)
    if not ex:
        return RESOURCE_NOT_FOUND_RESPONSE
    # TODO: Requests should have a auth token 
    # if not ex.belongs_to(current_identity):
    #     return NOT_AUTHORIZED_RESPONSE

    # The coordinates of the requested tile
    x = request.args.get('x')
    y = request.args.get('y')
    z = request.args.get('z')
    zlevel = request.args.get('zlevel')
    t = request.args.get('t')

    # Check arguments for validity and convert to integers
    if any([var is None for var in [x, y, z, zlevel, t]]):
        return MALFORMED_REQUEST_RESPONSE
    else:
        x, y, z, zlevel, t = map(int, [x, y, z, zlevel, t])

    mapobject_type = \
        db.session.query(MapobjectType).\
        filter_by(name=object_name).one()
    query_res = mapobject_type.get_mapobject_outlines_within_tile(
        x, y, z, t, zlevel)

    features = []

    if len(query_res) > 0:
        # Try to estimate how many points there are in total within 
        # the polygons of this tile.
        for mapobject_id, geom_geojson_str in query_res:
            feature = {
                "type": "Feature",
                "geometry": json.loads(geom_geojson_str),
                "properties": {
                    "id": mapobject_id
                }
            }
            features.append(feature)

    return jsonify({
        "type": "FeatureCollection",
        "features": features
    })
