# TmServer - TissueMAPS server application.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""User interface view functions that deal with layers."""
import json
import logging
from flask import jsonify, request, current_app, send_file
from flask_jwt import current_identity, jwt_required
from cStringIO import StringIO

import tmlib.models as tm
from tmlib.image import PyramidTile

from tmserver.api import api
from tmserver.util import decode_query_ids, decode_form_ids
from tmserver.util import assert_query_params, assert_form_params

logger = logging.getLogger(__name__)


@api.route(
    '/experiments/<experiment_id>/mapobjects/<object_name>/tile',
    methods=['GET']
)
@assert_query_params('x', 'y', 'z', 'zplane', 'tpoint')
@decode_query_ids(None)
def get_mapobjects_tile(experiment_id, object_name):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/mapobjects/(string:mapobject_type)/tile

        Sends all mapobject outlines as a GeoJSON feature collection
        that intersect with the tile at position x, y, z.
        If ``mapobject_type`` is ``DEBUG_TILE`` the outline returned
        will correspond to the tile boundaries.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "type": "FeatureCollection",
                "features": [
                    "type": "Feature",
                    "id": 1,
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [x1, y1], [x2, y2], ...
                        ]]
                    },
                    "properties": {
                        "type": "Cells"
                    }
                    ...
                ]
            }

        :query x: zero-based `x` coordinate
        :query y: zero-based `y` coordinate
        :query z: zero-based zoom level index
        :query zplane: the zplane of the associated layer
        :query tpoint: the time point of the associated layer

        :statuscode 200: no error
        :statuscode 400: malformed request

    """
    # The coordinates of the requested tile
    x = request.args.get('x', type=int)
    y = request.args.get('y', type=int)
    # "z" is the pyramid zoom level and "zlevel" the z-resolution of the
    # acquired image
    z = request.args.get('z', type=int)
    zplane = request.args.get('zplane', type=int)
    tpoint = request.args.get('tpoint', type=int)

    logger.debug(
        'get tile for mapobject of type "%s": x=%d, y=%d, z=%d, zplane=%d, '
        'tpoint=%d', object_name, x, y, z, zplane, tpoint
    )

    if object_name == 'DEBUG_TILE':
        with tm.utils.ExperimentSession(experiment_id) as session:
            layer = session.query(tm.ChannelLayers).first()
            maxzoom = layer.maxzoom_level_index
        minx, miny, maxx, maxy = tm.MapobjectSegmentation.bounding_box(
            x, y, z, maxzoom
        )
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

    with tm.utils.ExperimentSession(experiment_id) as session:
        mapobject_type = session.query(tm.MapobjectType).\
            filter_by(name=object_name).\
            one()
        query = mapobject_type.get_mapobject_outlines_within_tile(
            x, y, z, tpoint, zplane
        )

    features = []
    if len(query) > 0:
        # Try to estimate how many points there are in total within
        # the polygons of this tile.
        # TODO: Make this more light weight by sending binary coordinates
        # without GEOJSON overhead. Requires a hack on the client side.
        for mapobject_id, geom_geojson_str in query:
            logger.debug('include geometry of mapobject %d', mapobject_id)
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


@api.route(
    '/experiments/<experiment_id>/channel_layers/<channel_layer_id>/tiles',
    methods=['GET']
)
@assert_query_params('x', 'y', 'z')
@decode_query_ids(None)
def get_channel_layer_tile(experiment_id, channel_layer_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/channel_layer/(string:channel_layer_id)/tiles

        Sends a pyramid tile image for a specific channel layer.

        :query x: zero-based `x` coordinate
        :query y: zero-based `y` coordinate
        :query z: zero-based zoom level index

    """
    logger.info(
        'get tile for channel layer %d of experiment %d',
        channel_layer_id, experiment_id
    )
    x = request.args.get('x', type=int)
    y = request.args.get('y', type=int)
    z = request.args.get('z', type=int)

    with tm.utils.ExperimentSession(experiment_id) as session:
        channel_layer = session.query(tm.ChannelLayer).get(channel_layer_id)
        logger.debug(
            'get channel layer tile: x=%d, y=%d, z=%d, zplane=%d, tpoint=%d',
            x, y, z, channel_layer.zplane, channel_layer.tpoint
        )

        channel_layer_tile = session.query(tm.ChannelLayerTile).\
            filter_by(
                column=x, row=y, level=z,
                channel_layer_id=channel_layer.id
            ).\
            one_or_none()

        if channel_layer_tile is None:
            logger.warn('tile does not exist - create empty')
            tile = PyramidTile.create_as_background()
            pixels = tile.jpeg_encode()
        else:
            pixels = channel_layer_tile._pixels
        f = StringIO()
        f.write(pixels)
        f.seek(0)
        return send_file(f, mimetype='image/jpeg')


@api.route(
    '/experiments/<experiment_id>/label_layers/<label_layer_id>/tiles',
    methods=['GET']
)
@decode_query_ids(None)
@assert_query_params('x', 'y', 'z', 'zplane', 'tpoint')
def get_label_layer_tiles(experiment_id, label_layer_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/labellayers/(string:label_layer_id)/tiles

        Get all mapobjects together with the labels that were assigned to them
        for a given tool result and tile coordinate.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "type": "FeatureCollection",
                "features": [
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [x1, y1], [x2, y2], ...
                        ]]
                    },
                    "properties": {
                        "label": 123
                        "id": id
                    }
                    ...
                ]
            }

        :query x: zero-based `x` coordinate
        :query y: zero-based `y` coordinate
        :query z: zero-based zoom level index
        :query zplane: the zplane of the associated layer
        :query tpoint: the time point of the associated layer

        :statuscode 400: malformed request
        :statuscode 200: no error

    """
    # The coordinates of the requested tile
    x = request.args.get('x', type=int)
    y = request.args.get('y', type=int)
    z = request.args.get('z', type=int)
    zplane = request.args.get('zplane', type=int)
    tpoint = request.args.get('tpoint', type=int)

    with tm.utils.ExperimentSession(experiment_id) as session:
        label_layer = session.query(tm.LabelLayer).get(label_layer_id)
        result = session.query(tm.ToolResult).get(label_layer.tool_result_id)
        logger.info('get result tiles for label layer "%s"', label_layer.type)
        mapobject_type = session.query(tm.MapobjectType).\
            get(result.mapobject_type_id)
        query_res = mapobject_type.get_mapobject_outlines_within_tile(
            x, y, z, zplane=zplane, tpoint=tpoint
        )

        features = []
        has_mapobjects_within_tile = len(query_res) > 0

        if has_mapobjects_within_tile:
            mapobject_ids = [c[0] for c in query_res]
            mapobject_id_to_label = label_layer.get_labels(mapobject_ids)

            features = [
                {
                    'type': 'Feature',
                    'geometry': json.loads(geom_geojson_str),
                    'properties': {
                        'label': str(mapobject_id_to_label[id]),
                        'id': id
                     }
                }
                for id, geom_geojson_str in query_res
            ]

        return jsonify({
            'type': 'FeatureCollection',
            'features': features
        })

