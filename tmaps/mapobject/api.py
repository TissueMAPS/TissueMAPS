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

    ex = Experiment.get(experiment_id)
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

    mapobject_type = MapobjectType.query.filter_by(name=object_name).one()
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

#     # to query the database to return all objects contained within this polygon.
#     # The colon-prefixed placeholders are later filled in by sqlalchemy's text
#     # formatter.
#     bounding_polygon_str = \
#         '''(SELECT ST_MakePolygon(ST_GeomFromText('LINESTRING(:maxx :maxy,
#         :minx :maxy, :minx :miny, :maxx :miny, :maxx :maxy)')))'''


#     # NOTE: String formatting using '%' is OK here since we're not inserting
#     # user provided content directly. Everything has to go through the string
#     # formatting function of sqlalchemy.
#     if not use_simple_geom:
#         mapobject_query_str = '''
# SELECT
#     o.id, ST_AsGeoJSON(c.geom)
# FROM
#     mapobject_coords c JOIN mapobject o ON c.mapobject_id = o.id
# WHERE
#     c.z_level = :zlevel AND c.time = :t AND o.name = :object_name
#     AND ST_Intersects(%s, c.geom);
# ''' % bounding_polygon_str
#     else:
#         mapobject_query_str = '''
# SELECT
#     o.id, ST_AsGeoJSON(ST_Centroid(c.geom))
# FROM
#     mapobject_coords c JOIN mapobject o ON c.mapobject_id = o.id
# WHERE
#     c.z_level = :zlevel AND c.time = :t AND o.name = :object_name
#     AND ST_Intersects(%s, c.geom);
# ''' % bounding_polygon_str

#     res = db.engine.execute(
#         text(mapobject_query_str),
#         maxx=maxx, maxy=maxy, minx=minx, miny=miny, t=t, z=z,
#         zlevel=zlevel, object_name=object_name
#     )

#     # Tuples of the form (object_id, GeoJSON_geometry_object)
#     tuples = [(int(r[0]), json.loads(r[1])) for r in res.fetchall()]
#     features = \
#         [_create_mapobject_feature(obj_id=tpl[0], geometry_obj=tpl[1])
#          for tpl in tuples]
