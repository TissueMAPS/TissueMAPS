"""
API view functions for querying resources related to mapobjects
like their polygonal outlines or feature data.

"""
import os.path as p
import json
import logging
import numpy as np
from cStringIO import StringIO
from zipfile import ZipFile

from geoalchemy2.shape import to_shape
import skimage.draw

from flask_jwt import jwt_required
from flask_jwt import current_identity
from flask_jwt import jwt_required
from flask import jsonify, request, send_file
from sqlalchemy.sql import text
from werkzeug import secure_filename

import tmlib.models as tm
from tmlib.image import SegmentationImage

from tmserver.api import api
from tmserver.util import decode_query_ids, assert_query_params
from tmserver.error import MalformedRequestError, ResourceNotFoundError


logger = logging.getLogger(__name__)


@api.route(
    '/experiments/<experiment_id>/mapobjects/<object_name>/tile',
    methods=['GET']
)
@assert_query_params('x', 'y', 'z', 'zplane', 'tpoint')
@decode_query_ids()
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


@api.route('/experiments/<experiment_id>/features', methods=['GET'])
@jwt_required()
@decode_query_ids()
def get_features(experiment_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/features

        Get a list of feature objects supported for this experiment.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "data": {
                    "Cells": [
                        {
                            "name": "Cell_Area"
                        },
                        ...
                    ],
                    "Nuclei": [
                        ...
                    ],
                    ...
                }
            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 400: malformed request

    """
    with tm.utils.ExperimentSession(experiment_id) as session:
        features = session.query(tm.Feature).all()
        if not features:
            logger.waring('no features found')
        return jsonify({
            'data': features
        })


@api.route(
    '/experiments/<experiment_id>/mapobjects/<object_name>/segmentations',
    methods=['GET']
)
@jwt_required()
@assert_query_params('plate_name', 'well_name', 'x', 'y', 'zplane', 'tpoint')
@decode_query_ids()
def get_mapobjects_segmentation(experiment_id, object_name):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/mapobjects/(string:mapobject_type)/segmentations

        Get the segmentation image at a specified coordinate.

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 400: malformed request

        :query plate_name: the plate's name
        :query well_name: the well's name
        :query x: x-coordinate
        :query y: y-coordinate
        :query zplane: the zplane
        :query tpoint: the time point

    """
    plate_name = request.args.get('plate_name')
    well_name = request.args.get('well_name')
    # TODO: raise MissingGETParameterError when arg missing
    x = request.args.get('x', type=int)
    y = request.args.get('y', type=int)
    zplane = request.args.get('zplane', type=int)
    tpoint = request.args.get('tpoint', type=int)
    label = request.args.get('label', None)
    with tm.utils.MainSession() as session:
        experiment = session.query(tm.ExperimentReference).get(experiment_id)
        experiment_name = experiment.name

    with tm.utils.ExperimentSession(experiment_id) as session:
        site = session.query(tm.Site).\
            join(tm.Well).\
            join(tm.Plate).\
            filter(
                tm.Plate.name == plate_name,
                tm.Well.name == well_name,
                tm.Site.x == x, tm.Site.y == y
            ).\
            one()
        mapobject_type = session.query(tm.MapobjectType).\
            filter_by(name=object_name).\
            one()
        segmentations = session.query(
                tm.MapobjectSegmentation.label,
                tm.MapobjectSegmentation.geom_poly
            ).\
            join(tm.Mapobject).\
            join(tm.MapobjectType).\
            filter(
                tm.MapobjectType.name == object_name,
                tm.MapobjectSegmentation.site_id == site.id,
                tm.MapobjectSegmentation.zplane == zplane,
                tm.MapobjectSegmentation.tpoint == tpoint
            ).\
            all()

        if len(segmentations) == 0:
            raise ResourceNotFoundError('No segmentations found.')
        polygons = dict()
        for seg in segmentations:
            polygons[(tpoint, zplane, seg.label)] = seg.geom_poly

        height = site.height - (
            site.intersection.lower_overhang + site.intersection.upper_overhang
        )
        width = site.width - (
            site.intersection.left_overhang + site.intersection.right_overhang
        )
        y_offset, x_offset = site.offset
        y_offset += site.intersection.lower_overhang
        x_offset += site.intersection.right_overhang

        filename = '%s_%s_x%.3d_y%.3d_z%.3d_t%.3d_%s.png' % (
            experiment_name, site.well.name, site.x, site.y, zplane, tpoint,
            object_name
        )

    img = SegmentationImage.create_from_polygons(
        polygons, y_offset, x_offset, (height, width)
    )
    f = StringIO()
    f.write(img.encode('png'))
    f.seek(0)
    return send_file(
        f,
        attachment_filename=secure_filename(filename),
        mimetype='image/png',
        as_attachment=True
    )


@api.route(
    '/experiments/<experiment_id>/mapobjects/<object_name>/feature-values',
    methods=['GET']
)
@jwt_required()
@decode_query_ids()
def get_feature_values(experiment_id, object_name):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/mapobjects/(string:mapobject_type)/feature-values

        Get all feature values for a given ``mapobject_type`` as a
        zip-compressed CSV file.

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 400: malformed request

    """
    with tm.utils.MainSession() as session:
        experiment = session.query(tm.ExperimentReference).get(experiment_id)
        experiment_name = experiment.name

    with tm.utils.ExperimentSession(experiment_id) as session:
        mapobject_type = session.query(tm.MapobjectType).\
            filter_by(name=object_name).\
            one()
        features = mapobject_type.get_feature_value_matrix()
        metadata = mapobject_type.get_metadata_matrix()

    if features.values.shape[0] != metadata.values.shape[0]:
        raise ValueError(
            'Features and metadata must have same number of "%s" objects'
            % object_name
        )
    if any(features.index.values != metadata.index.values):
        raise ValueError(
            'Features and metadata must have the same index.'
        )
    basename = secure_filename(
        '%s_%s_features' % (experiment_name, object_name)
    )
    data_filename = '%s_data.csv' % basename
    metadata_filename = '%s_metadata.csv' % basename
    f = StringIO()
    with ZipFile(f, 'w') as zf:
        zf.writestr(
            data_filename,
            features.to_csv(None, encoding='utf-8', index=False)
        )
        zf.writestr(
            metadata_filename,
            metadata.to_csv(None, encoding='utf-8', index=False)
        )
    f.seek(0)
    # TODO: These files may become very big, we may need to use a generator to
    # stream the file: http://flask.pocoo.org/docs/0.11/patterns/streaming
    # On the client side the streaming requests can be handled by an iterator:
    # http://docs.python-requests.org/en/master/user/advanced/#streaming-requests
    return send_file(
        f,
        attachment_filename='%s.zip' % basename,
        mimetype='application/octet-stream',
        as_attachment=True
    )
