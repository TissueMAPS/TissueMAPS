import os.path as p
from tmaps.api import api

from flask.ext.jwt import jwt_required
from flask.ext.jwt import current_identity
from flask.ext.jwt import jwt_required

from tmaps.mapobjects import FastRtree, MapObject

from flask import jsonify, request, current_app
from tmaps.models import Experiment
from tmaps.api.responses import (
    MALFORMED_REQUEST_RESPONSE,
    RESOURCE_NOT_FOUND_RESPONSE,
    NOT_AUTHORIZED_RESPONSE
)

@api.route('/experiments/<experiment_id>/mapobjects/<object_type>', methods=['GET'])
def get_mapobjects_tile(experiment_id, object_type):

    ex = Experiment.get(experiment_id)
    if not ex:
        return RESOURCE_NOT_FOUND_RESPONSE
    # TODO: Requests should have a auth token 
    # if not ex.belongs_to(current_identity):
    #     return NOT_AUTHORIZED_RESPONSE

    x = int(request.args.get('x'))
    y = int(request.args.get('y'))
    z = int(request.args.get('z'))

    if x is None or y is None or z is None:
        return MALFORMED_REQUEST_RESPONSE

    print "x: %s, y: %s, z: %s" % (str(x), str(y), str(z))

    # width = 15860
    # height = -9140

    # the tile width/height expressed in coordinates on the highest zoom level
    size = 256 * 2 ** (6 - z)

    # topleft corner
    x0 = x * size
    y0 = y * size

    # bounding box
    minx = x0
    maxx = x0 + size
    miny = -y0 - size
    maxy = -y0
    bbox = (minx, miny, maxx, maxy)

    rtree_filename = p.join(ex.location, 'cells_rtree')

    idx = FastRtree(rtree_filename)

    mapobjects = [node.object for node in idx.intersection(bbox, objects=True)]

    use_simple_geom = z < 3

    def mapobject_to_geojson_feature(mapobject, use_simple_geom):
        if use_simple_geom:
            # 2d array is nested in an additional list
            coordinates = mapobject.centroid.tolist()
        else:
            # 2d array is nested in an additional list
            coordinates = [ mapobject.outline.tolist() ]
        geometry_type = 'Point' if use_simple_geom else 'Polygon'
        return {
            "type": "Feature",
            "geometry": {
                "type": geometry_type,
                "coordinates": coordinates
            },
            "properties": {
                "id": str(mapobject.id)
            }
        }

    features = [mapobject_to_geojson_feature(o, use_simple_geom) for o in mapobjects]

    return jsonify(
        {
            "type": "FeatureCollection",
            "features": features
        }
    )
    

