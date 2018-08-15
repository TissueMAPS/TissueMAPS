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
"""API view functions for querying :mod:`tile <tmlib.models.tile>` resources.
"""
import json
import logging
import numpy as np
from flask import jsonify, request, send_file
from flask_jwt import jwt_required
from cStringIO import StringIO
from sqlalchemy import case

import tmlib.models as tm
from tmlib.image import PyramidTile

from tmserver.api import api
from tmserver.util import (
    decode_query_ids, decode_form_ids, assert_query_params, assert_form_params
)

logger = logging.getLogger(__name__)


@api.route(
    '/experiments/<experiment_id>/channel_layers/<channel_layer_id>/tiles',
    methods=['GET']
)
@assert_query_params('x', 'y', 'z')
@decode_query_ids(None)
def get_channel_layer_tile(experiment_id, channel_layer_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/channel_layer/(string:channel_layer_id)/tiles

        Sends a :class:`ChannelLayerTile <tmlib.models.tile.ChannelLayerTile`.

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
        tile = session.query(tm.ChannelLayerTile).\
            filter_by(channel_layer_id=channel_layer.id, z=z, y=y, x=x).\
            one_or_none()
        if tile is not None:
            # TODO: We shouldn't access the "privat" attribute, but it's more
            # performant in this case, since it provides direct access to the
            # column without accessing the property.
            pixels = tile._pixels
            # pixels = tile.pixels.jpeg_encode()
        else:
            logger.warn('tile does not exist - create empty')
            tile = PyramidTile.create_as_background()
            pixels = tile.jpeg_encode()
        f = StringIO()
        f.write(pixels)
        f.seek(0)
        return send_file(f, mimetype='image/jpeg')


@api.route(
    '/experiments/<experiment_id>/segmentation_layers/<segmentation_layer_id>/tiles',
    methods=['GET']
)
@assert_query_params('x', 'y', 'z')
@decode_query_ids(None)
def get_segmentation_layer_tile(experiment_id, segmentation_layer_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/segmentation_layers/(string:segmentation_layer_id)/tile

        Sends each the geometric representation of each
        :class:`MapobjectSegmentation <tmlib.models.mapobject.MapobjectSegmentation>`
        as a GeoJSON feature collection that intersect with the given Pyramid
        tile at position x, y, z.

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

        :statuscode 200: no error
        :statuscode 400: malformed request

    """
    # The coordinates of the requested tile
    x = request.args.get('x', type=int)
    y = request.args.get('y', type=int)
    # "z" is the pyramid zoom level and "zlevel" the z-resolution of the
    # acquired image
    z = request.args.get('z', type=int)

    logger.debug(
        'get tile for segmentation layer %d : x=%d, y=%d, z=%d',
        segmentation_layer_id, x, y, z
    )

    # if mapobject_type_name == 'DEBUG_TILE':
    #     with tm.utils.ExperimentSession(experiment_id) as session:
    #         layer = session.query(tm.ChannelLayer).first()
    #         # TODO: "maxzoom" should be stored in Experiment
    #         maxzoom = layer.maxzoom_level_index
    #     minx, miny, maxx, maxy = tm.SegmentationLayer.get_tile_bounding_box(
    #         x, y, z, maxzoom
    #     )
    #     return jsonify({
    #         'type': 'Feature',
    #         'geometry': {
    #             'type': 'Polygon',
    #             'coordinates': [[
    #                 [maxx, maxy], [minx, maxy], [minx, miny], [maxx, miny],
    #                 [maxx, maxy]
    #             ]]
    #         },
    #         'properties': {
    #             'x': x, 'y': y, 'z': z,
    #             'type': 'DEBUG_TILE'
    #         }
    #     })

    with tm.utils.ExperimentSession(experiment_id) as session:
        segmentation_layer = session.query(tm.SegmentationLayer).get(
            segmentation_layer_id
        )
        outlines = segmentation_layer.get_segmentations(x, y, z)
        mapobject_type_name = segmentation_layer.mapobject_type.name

    # Try to estimate how many points there are in total within
    # the polygons of this tile.
    # TODO: Make this more light weight by sending binary coordinates
    # without GEOJSON overhead. Requires a hack on the client side.
    if len(outlines) > 0:
        features = [
            {
                'type': 'Feature',
                'id': mapobject_id,
                'geometry': json.loads(geom_geojson_str),
                'properties': {
                    'type': mapobject_type_name
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


@api.route(
    '/experiments/<experiment_id>/segmentation_layers/<segmentation_layer_id>/labeled_tiles',
    methods=['GET']
)
@decode_query_ids(None)
@assert_query_params('x', 'y', 'z', 'result_name')
def get_segmentation_layer_label_tile(experiment_id, segmentation_layer_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/segmentation_layers/(string:segmentation_layer_id)/labeled_tiles

        Sends each the geometric representation of each
        :class:`MapobjectSegmentation <tmlib.models.mapobject.MapobjectSegmentation>`
        as a GeoJSON feature collection that intersect with the given Pyramid
        tile at position x, y, z together with the
        :class:`LabelValues <tmlib.models.result.LabelValues>` for the specified
        tool :class:`Result <tmlib.models.result.Result>`.

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
                        "label": 123
                    }
                    ...
                ]
            }

        :query x: zero-based `x` coordinate
        :query y: zero-based `y` coordinate
        :query z: zero-based zoom level index

        :statuscode 400: malformed request
        :statuscode 200: no error

    """
    # The coordinates of the requested tile
    x = request.args.get('x', type=int)
    y = request.args.get('y', type=int)
    z = request.args.get('z', type=int)
    result_name = request.args.get('result_name')

    logger.debug(
        'get labeled tile for segmentation layer of tool result "%s": '
        'x=%d, y=%d, z=%d', result_name, x, y, z
    )
    with tm.utils.ExperimentSession(experiment_id) as session:
        segmentation_layer = session.query(tm.SegmentationLayer).\
            get(segmentation_layer_id)
        outlines = segmentation_layer.get_segmentations(x, y, z)
        mapobject_type = segmentation_layer.mapobject_type
        mapobject_type_name = mapobject_type.name

        result = session.query(tm.ToolResult).\
            filter_by(name=result_name, mapobject_type_id=mapobject_type.id).\
            one()

        if len(outlines) > 0:
            mapobject_ids = [c.mapobject_id for c in outlines]
            mapobject_id_to_label = result.get_labels(mapobject_ids)
            features = [
                {
                    'type': 'Feature',
                    'id': mapobject_id,
                    'geometry': json.loads(geom_geojson_str),
                    'properties': {
                        'label': str(mapobject_id_to_label[mapobject_id])
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

