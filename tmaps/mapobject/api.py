import os.path as p
import json

from flask.ext.jwt import jwt_required
from flask.ext.jwt import current_identity
from flask.ext.jwt import jwt_required
from flask import jsonify, request

from tmaps.api import api
from tmaps.extensions.database import db

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


@api.route('/experiments/<experiment_id>/mapobjects/<object_type>', methods=['GET'])
def get_mapobjects_tile(experiment_id, object_type):

    ex = Experiment.get(experiment_id)
    if not ex:
        return RESOURCE_NOT_FOUND_RESPONSE
    # TODO: Requests should have a auth token 
    # if not ex.belongs_to(current_identity):
    #     return NOT_AUTHORIZED_RESPONSE

    # The coordinates of the requested tile
    x = int(request.args.get('x'))
    y = int(request.args.get('y'))
    z = int(request.args.get('z'))

    if x is None or y is None or z is None:
        return MALFORMED_REQUEST_RESPONSE

    # The tile width/height expressed in coordinates on the highest zoom level
    size = 256 * 2 ** (6 - z)
    # Topleft corner
    x0 = x * size
    y0 = y * size
    # Bounding box
    minx = x0
    maxx = x0 + size
    miny = -y0 - size
    maxy = -y0

    # A SQL PostGIS statement to produce a polygon that is later used
    # to query the database to return all objects contained within this polygon.
    bounding_polygon_str = '''(SELECT ST_MakePolygon(ST_GeomFromText('LINESTRING(%d %d, %d %d, %d %d, %d %d, %d %d)')))''' % (
        maxx, maxy,
        minx, maxy,
        minx, miny,
        maxx, miny,
        maxx, maxy
    )

    use_simple_geom = z < 3

    if not use_simple_geom:
        mapobject_query_str = '''
SELECT obj_id, ST_AsGeoJSON(geom) FROM mapobject
WHERE ST_Contains(%s, mapobject.geom)
''' % bounding_polygon_str
    else:
        mapobject_query_str = '''
SELECT obj_id, ST_AsGeoJSON(ST_Centroid(geom)) FROM mapobject
WHERE ST_Contains(%s, mapobject.geom)
''' % bounding_polygon_str

    res = db.engine.execute(mapobject_query_str)

    # Tuples of the form (object_id, GeoJSON_geometry_object)
    tuples = [(int(r[0]), json.loads(r[1])) for r in res.fetchall()]
    features = [_create_mapobject_feature(obj_id=t[0], geometry_obj=t[1]) for t in tuples]

    return jsonify(
        {
            "type": "FeatureCollection",
            "features": features
        }
    )
    

