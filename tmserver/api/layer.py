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
import numpy as np
from flask import jsonify, request, current_app, send_file
from flask_jwt import current_identity, jwt_required
from cStringIO import StringIO

import tmlib.models as tm
from tmlib.image import PyramidTile
from tmlib.models.mapobject import get_mapobject_outlines_within_tile

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
        # TODO
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

    outlines = get_mapobject_outlines_within_tile(
        experiment_id, object_name, x, y, z, tpoint, zplane
    )
    # Try to estimate how many points there are in total within
    # the polygons of this tile.
    # TODO: Make this more light weight by sending binary coordinates
    # without GEOJSON overhead. Requires a hack on the client side.
    if len(outlines) > 0:
        features = [
            {
                "type": "Feature",
                "id": mapobject_id,
                "geometry": json.loads(geom_geojson_str),
                "properties": {
                    "type": object_name
                }
            }
            for mapobject_id, geom_geojson_str in outlines
        ]
    else:
        features = []

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
    x = request.args.get('x', type=int)
    y = request.args.get('y', type=int)
    z = request.args.get('z', type=int)

    logger.debug(
        'get tile for channel layer %d of experiment %d: x=%d, y=%d, z=%d',
        channel_layer_id, experiment_id, x, y, z
    )

    with tm.utils.ExperimentSession(experiment_id) as session:
        channel_layer = session.query(tm.ChannelLayer).get(channel_layer_id)
        logger.debug(
            'get channel layer tile: x=%d, y=%d, z=%d, zplane=%d, tpoint=%d',
            x, y, z, channel_layer.zplane, channel_layer.tpoint
        )
        layer_id = channel_layer.id

    with tm.utils.ExperimentConnection(experiment_id) as connection:
        connection.execute('''
            SELECT pixels FROM channel_layer_tiles
            WHERE level=%(level)s
            AND "row"=%(row)s
            AND "column"=%(column)s
            AND channel_layer_id=%(channel_layer_id)s;
        ''', {
            'level': z, 'row': y, 'column': x, 'channel_layer_id': layer_id
        })
        tile = connection.fetchone()
        if tile is not None:
            pixels = np.frombuffer(tile.pixels, np.uint8)
        else:
            logger.warn('tile does not exist - create empty')
            tile = PyramidTile.create_as_background()
            pixels = tile.jpeg_encode()
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
def get_label_layer_tile(experiment_id, label_layer_id):
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
        layer = session.query(tm.LabelLayer).get(label_layer_id)
        result = session.query(tm.ToolResult).get(layer.tool_result_id)
        logger.debug(
            'get result tile for label layer of type "%s": '
            'x=%d, y=%d, z=%d, tpoint=%d, zplane%d',
            layer.type, x, y, z, tpoint, zplane
        )
        mapobject_type = session.query(tm.MapobjectType).\
            get(result.mapobject_type_id)

        outlines = get_mapobject_outlines_within_tile(
            experiment_id, mapobject_type.name, x, y, z, tpoint, zplane
        )

        if len(outlines) > 0:
            mapobject_ids = [c.mapobject_id for c in outlines]
            mapobject_id_to_label = layer.get_labels(mapobject_ids)

            features = [
                {
                    'type': 'Feature',
                    'geometry': json.loads(geom_geojson_str),
                    'properties': {
                        'label': str(mapobject_id_to_label[mapobject_id]),
                        'id': mapobject_id
                     }
                }
                for mapobject_id, geom_geojson_str in outlines
            ]
        else:
            features = []

    return jsonify({
        'type': 'FeatureCollection',
        'features': features
    })

