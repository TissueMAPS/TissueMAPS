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
"""API view functions for querying resources related to mapobjects
like their polygonal outlines or feature data.
"""
import os.path as p
import json
import logging
import numpy as np
import pandas as pd
from cStringIO import StringIO
from zipfile import ZipFile
from geoalchemy2.shape import to_shape
import skimage.draw
from flask_jwt import current_identity, jwt_required
from flask import jsonify, request, send_file, Response
from sqlalchemy.sql import text
from sqlalchemy.orm.exc import NoResultFound
from werkzeug import secure_filename

import tmlib.models as tm
from tmlib.image import SegmentationImage
from tmlib.utils import create_partitions

from tmserver.api import api
from tmserver.util import decode_query_ids, assert_query_params
from tmserver.error import MalformedRequestError, ResourceNotFoundError


logger = logging.getLogger(__name__)


@api.route('/experiments/<experiment_id>/features', methods=['GET'])
@jwt_required()
@decode_query_ids('read')
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
    '/experiments/<experiment_id>/mapobjects/<mapobject_type_name>/segmentations',
    methods=['GET']
)
@jwt_required()
@assert_query_params('plate_name', 'well_name', 'x', 'y', 'zplane', 'tpoint')
@decode_query_ids('read')
def get_segmentation_image(experiment_id, mapobject_type_name):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/mapobjects/(string:mapobject_type_name)/segmentations

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
        site_mapobject_type = session.query(tm.MapobjectType.id).\
            filter_by(ref_type=tm.Site.__name__).\
            one()
        site_segmentation = session.query(tm.MapobjectSegmentation.geom_polygon).\
            join(tm.Mapobject).\
            filter(tm.Mapobject.ref_id == site.id).\
            filter(tm.Mapobject.mapobject_type_id == site_mapobject_type.id).\
            one()
        segmentation_layer = session.query(tm.SegmentationLayer.id).\
            join(tm.MapobjectType).\
            filter(
                tm.MapobjectType.name == mapobject_type_name,
                tm.SegmentationLayer.tpoint == tpoint,
                tm.SegmentationLayer.zplane == zplane,
            ).\
            one()

        # Retrieve all mapobjects of the given type that fall within the given
        # site and label them according to the ID that was assigned to them,
        # assuming that IDs were assigned in the order of original labels.
        segmentations = session.query(tm.MapobjectSegmentation.geom_polygon).\
            filter_by(segmentation_layer_id=segmentation_layer.id).\
            filter(
                tm.MapobjectSegmentation.geom_polygon.ST_Intersects(
                    site_segmentation.geom_polygon
                )
            ).\
            order_by(tm.MapobjectSegmentation.id).\
            all()

        if len(segmentations) == 0:
            raise ResourceNotFoundError(tm.MapobjectSegmentation, request.args)
        polygons = dict()
        for i, seg in enumerate(segmentations):
            polygons[(tpoint, zplane, i+1)] = seg.geom_polygon

        y_offset, x_offset = site.offset
        height = site.height
        width = site.width
        if site.intersection is not None:
            height = height - (
                site.intersection.lower_overhang +
                site.intersection.upper_overhang
            )
            width = width - (
                site.intersection.left_overhang +
                site.intersection.right_overhang
            )
            y_offset += site.intersection.lower_overhang
            x_offset += site.intersection.right_overhang

        filename = '%s_%s_x%.3d_y%.3d_z%.3d_t%.3d_%s.png' % (
            experiment_name, site.well.name, site.x, site.y, zplane, tpoint,
            mapobject_type_name
        )

    img = SegmentationImage.create_from_polygons(
        polygons, y_offset, x_offset, (height, width)
    )
    f = StringIO()
    f.write(img.png_encode())
    f.seek(0)
    return send_file(
        f,
        attachment_filename=secure_filename(filename),
        mimetype='image/png',
        as_attachment=True
    )


@api.route(
    '/experiments/<experiment_id>/mapobjects/<mapobject_type_name>/feature-values',
    methods=['GET']
)
@jwt_required()
@decode_query_ids('read')
def get_mapobject_feature_values(experiment_id, mapobject_type_name):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/mapobjects/(string:mapobject_type_name)/feature-values

        Get all feature values
        (:class:`FeatureValue.values <tmlib.models.feature.FeatureValue.values>`)
        for objects of the given
        :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`
        as a *n*x*p* *CSV* table, where *n* is the number of
        mapobjects (:class:`Mapobject <tmlib.models.mapobject.Mapobject>`) and
        *p* is the number of features
        (:class:`Feature <tmlib.models.feature.Feature>`).

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 400: malformed request
        :statuscode 401: unauthorized
        :statuscode 404: not found

    .. note:: The first row of the table are column (feature) names.
    """
    with tm.utils.MainSession() as session:
        experiment = session.query(tm.ExperimentReference).get(experiment_id)
        experiment_name = experiment.name

    with tm.utils.ExperimentSession(experiment_id) as session:
        try:
            mapobject_type = session.query(tm.MapobjectType).\
                filter_by(name=mapobject_type_name).\
                one()
            mapobject_type_id = mapobject_type.id
        except NoResultFound:
            raise ResourceNotFoundError(
                tm.MapobjectType, {'mapobject_type_name': mapobject_type_name}
            )

    def generate_feature_matrix(mapobject_type_id):
        with tm.utils.ExperimentSession(experiment_id) as session:
            n_mapobjects = session.query(tm.Mapobject.id).\
                filter_by(mapobject_type_id=mapobject_type_id).\
                count()

            features = session.query(tm.Feature.name).\
                filter_by(mapobject_type_id=mapobject_type_id).\
                order_by(tm.Feature.id).\
                all()
            feature_names = [f.name for f in features]

            # First line of CSV are column names
            yield ','.join(feature_names) + '\n'
            # Loading all feature values into memory may cause problems for
            # really large datasets. Therefore, we perform several queries
            # each returning only a few thousand objects at once.
            # Performing a query for each object would create too much overhead.
            batch_size = 10000
            for n in xrange(int(np.ceil(n_mapobjects / float(batch_size)))):
                # One could nicely filter values using slice()
                feature_values = session.query(tm.FeatureValues.values).\
                    join(tm.Mapobject).\
                    filter(tm.Mapobject.mapobject_type_id == mapobject_type_id).\
                    order_by(tm.Mapobject.id).\
                    limit(batch_size).\
                    offset(n).\
                    all()
                for v in feature_values:
                    # The keys in a dictionary don't have any order.
                    # Values must be sorted based on feature_id, such that they
                    # end up in the correct column of the CSV table matching
                    # the corresponding column names.
                    values = [v.values[k] for k in sorted(v.values)]
                    yield ','.join(values) + '\n'

    return Response(
        generate_feature_matrix(mapobject_type_id),
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename={filename}'.format(
                filename='{experiment}_{object_type}_feature-values.csv'.format(
                    experiment=experiment_name,
                    object_type=mapobject_type_name
                )
            )
        }
    )

@api.route(
    '/experiments/<experiment_id>/mapobjects/<mapobject_type_name>/metadata',
    methods=['GET']
)
@jwt_required()
@decode_query_ids('read')
def get_mapobject_metadata(experiment_id, mapobject_type_name):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/mapobjects/(string:mapobject_type_name)/metadata

        Get :class:`FeatureValue <tmlib.models.feature.FeatureValue>` for
        the given :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`
        as a *n*x*p* feature table, where *n* is the number of
        mapobjects (:class:`Mapobject <tmlib.models.mapobject.Mapobject>`) and
        *p* is the number of features
        (:class:`Feature <tmlib.models.feature.Feature>`).
        The table is send in form of a *CSV* file with the first representing
        feature names.

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 400: malformed request
        :statuscode 401: unauthorized
        :statuscode 404: not found

    """
    with tm.utils.MainSession() as session:
        experiment = session.query(tm.ExperimentReference).get(experiment_id)
        experiment_name = experiment.name

    with tm.utils.ExperimentSession(experiment_id) as session:
        try:
            mapobject_type = session.query(tm.MapobjectType).\
                filter_by(name=mapobject_type_name).\
                one()
            mapobject_type_id = mapobject_type.id
        except NoResultFound:
            raise ResourceNotFoundError(
                tm.MapobjectType, {'mapobject_type_name': mapobject_type_name}
            )

    def generate_feature_matrix(mapobject_type_id):
        with tm.utils.ExperimentSession(experiment_id) as session:
            n_mapobjects = session.query(tm.Mapobject.id).\
                filter_by(mapobject_type_id=mapobject_type_id).\
                count()

            locations = pd.DataFrame(
                session.query(
                    tm.Site.id, tm.Site.y, tm.Site.x,
                    tm.Well.name, tm.Plate.name,
                ).\
                join(tm.Well).\
                join(tm.Plate).\
                all()
            )
            locations.set_index('site_id', inplace=True)
            # First line of CSV are column names
            names = [
                'id', 'label', 'tpoint', 'zplane',
                'site_y', 'site_x', 'well_name', 'plate_name'
            ]
            yield ','.join(names) + '\n'
            batch_size = 10000
            for n in xrange(np.ceil(n_mapobjects / float(batch_size))):
                segmentations = session.query(
                        tm.MapobjectSegmentation.mapobject_id,
                        tm.MapobjectSegmentation.label,
                        tm.MapobjectSegmentation.tpoint,
                        tm.MapobjectSegmentation.zplane,
                    ).\
                    join(tm.Mapobject).\
                    filter(tm.Mapobject.mapobject_type_id == mapobject_type_id).\
                    order_by(tm.MapobjectSegmentation.site_id).\
                    limit(batch_size).\
                    offset(n).\
                    all()
                for segm in segmentations:
                    values = [str(v) for v in segm]
                    values += [str(v) for v in locations.loc[segm.site_id, :]]
                    yield ','.join(values) + '\n'

    return Response(
        generate_feature_matrix(mapobject_type_id),
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename={filename}'.format(
                filename='{experiment}_{object_type}_metadata.csv'.format(
                    experiment=experiment_name,
                    object_type=mapobject_type_name
                )
            )
        }
    )

