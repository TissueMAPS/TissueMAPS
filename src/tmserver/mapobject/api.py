import os.path as p
import json

from flask.ext.jwt import jwt_required
from flask.ext.jwt import current_identity
from flask.ext.jwt import jwt_required
from flask import jsonify, request
from sqlalchemy.sql import text

from tmserver.api import api
from tmserver.extensions import db

from tmserver.mapobject import MapobjectSegmentation, MapobjectType
from tmserver.experiment import Experiment


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
    # "z" is the pyramid zoom level and "zlevel" the z-resolution of the
    # acquired image
    z = request.args.get('z')
    zplane = request.args.get('zlevel')
    t = request.args.get('t')

    # Check arguments for validity and convert to integers
    if any([var is None for var in [x, y, z, zplane, t]]):
        return MALFORMED_REQUEST_RESPONSE
    else:
        x, y, z, zplane, t = map(int, [x, y, z, zplane, t])

    if object_name == 'DEBUG_TILE':
        maxzoom = ex.channels[0].layers[0].maxzoom_level_index
        minx, miny, maxx, maxy = MapobjectSegmentation.bounding_box(x, y, z, maxzoom)
        return jsonify({
            'type': 'Feature',
            'geometry': {
                'type': 'Polygon',
                'coordinates': [[
                    [maxx, maxy], [minx, maxy], [minx, miny], [maxx, miny],
                    [maxx, maxy]
                ]]
            },
            'properties': {
                'x': x,
                'y': y,
                'z': z,
                'type': 'DEBUG_TILE'
            }
        })

    mapobject_type = db.session.query(MapobjectType).\
        filter_by(name=object_name, experiment_id=ex.id).\
        one()
    query_res = mapobject_type.get_mapobject_outlines_within_tile(
        x, y, z, t, zplane
    )

    features = []

    if len(query_res) > 0:
        # Try to estimate how many points there are in total within
        # the polygons of this tile.
        # TODO: Make this more light weight by sending binary coordinates
        # without GEOJSON overhead. Requires a hack on the client side.
        for mapobject_id, geom_geojson_str in query_res:
            feature = {
                "type": "Feature",
                "id": mapobject_id,
                "geometry": json.loads(geom_geojson_str),
                "properties": {
                    "type": object_name
                }
            }
            features.append(feature)

    return jsonify({
        "type": "FeatureCollection",
        "features": features
    })
