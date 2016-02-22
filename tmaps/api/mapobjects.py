from tmaps.api import api

from flask import jsonify, request, current_app
from tmaps.api.responses import (
    MALFORMED_REQUEST_RESPONSE,
    RESOURCE_NOT_FOUND_RESPONSE,
    NOT_AUTHORIZED_RESPONSE
)


@api.route('/experiments/<experiment_id>/mapobjects/<object_type>', methods=['GET'])
def get_mapobjects_tile(experiment_id, object_type):

    x = request.args.get('x')
    y = request.args.get('y')
    z = request.args.get('z')

    if x is None or y is None or z is None:
        return MALFORMED_REQUEST_RESPONSE

    return jsonify(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                    "type": "Polygon",
                        "coordinates": [
                          [ [100.0, 0.0], [101.0, 0.0], [101.0, 1.0],
                            [100.0, 1.0], [100.0, 0.0] ]
                          ]
                   },
                   "properties": { "id": "0" }
               },
               {
                   "type": "Feature",
                   "geometry": {
                   "type": "Polygon",
                       "coordinates": [
                         [ [100.0, 0.0], [101.0, 0.0], [101.0, 1.0],
                           [100.0, 1.0], [100.0, 0.0] ]
                         ]
                  },
                  "properties": { "id": "1" }
               }
            ]
        }
    )

    # return jsonify({
    #     'mapobjects': [
    #         {
    #             'id': 20,
    #             'outline': {
    #                 x: [1, 2, 3, 4, 5],
    #                 y: [1, 2, 3, 4, 5]
    #             }
    #         },
    #         {
    #             'id': 22,
    #             'outline': {
    #                 x: [1, 2, 3, 4, 5],
    #                 y: [1, 2, 3, 4, 5]
    #             }
    #         }
    #     ]
    # })

    

