# from tmaps.api import api

# from flask.ext.jwt import jwt_required
# from flask.ext.jwt import current_identity

# from flask import jsonify, request, current_app
# from tmaps.api.responses import (
#     MALFORMED_REQUEST_RESPONSE,
#     RESOURCE_NOT_FOUND_RESPONSE,
#     NOT_AUTHORIZED_RESPONSE
# )


# @api.route('/experiments/<experiment_id>/mapobjects/<object_type>', methods=['GET'])
# @jwt_required()
# def get_mapobjects_tile(experiment_id, object_type):

#     ex = Experiment.get(experiment_id)
#     if not ex:
#         return RESOURCE_NOT_FOUND_RESPONSE
#     if not ex.belongs_to(current_identity):
#         return NOT_AUTHORIZED_RESPONSE
#     if x is None or y is None or z is None:
#         return MALFORMED_REQUEST_RESPONSE

#     x = int(request.args.get('x'))
#     y = int(request.args.get('y'))
#     z = int(request.args.get('z'))
#     print "x: %s, y: %s, z: %s" % (str(x), str(y), str(z))

#     # if ex.has_dataset:
#     #     with ex.dataset as data:
#     #         pass
#     # width = 15860
#     # height = -9140

#     size = 256 * 2 ** (6 - z)
#     x0 = x * size
#     y0 = y * size

#     return jsonify(
#         {
#             "type": "FeatureCollection",
#             "features": [
#                 {
#                     "type": "Feature",
#                     "geometry": {
#                     "type": "Polygon",
#                         "coordinates": [[
#                             [x0 + size, -y0],
#                             [x0,        -y0],
#                             [x0,        -y0 - size],
#                             [x0 + size, -y0 - size],
#                             [x0 + size, -y0]
#                      ]]
#                    },
#                    "properties": { "id": "0" }
#                }
#             ]
#         }
#     )
    

