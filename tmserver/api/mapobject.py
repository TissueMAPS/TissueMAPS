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

from tmserver.api import api
from tmserver.util import (
    decode_query_ids, assert_query_params, check_permissions
)
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
    '/experiments/<experiment_id>/mapobjects/<object_type>/segmentations',
    methods=['GET']
)
@jwt_required()
@assert_query_params('plate_name', 'well_name', 'x', 'y', 'zplane', 'tpoint')
@decode_query_ids('read')
def get_segmentation_image(experiment_id, object_type):
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
            filter_by(name=object_type).\
            one()
        segmentations = session.query(
                tm.MapobjectSegmentation.label,
                tm.MapobjectSegmentation.geom_poly
            ).\
            join(tm.Mapobject).\
            join(tm.MapobjectType).\
            filter(
                tm.MapobjectType.name == object_type,
                tm.MapobjectSegmentation.site_id == site.id,
                tm.MapobjectSegmentation.zplane == zplane,
                tm.MapobjectSegmentation.tpoint == tpoint
            ).\
            all()

        if len(segmentations) == 0:
            raise ResourceNotFoundError(tm.MapobjectSegmentation, request.args)
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
            object_type
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
    '/experiments/<experiment_id>/mapobjects/<object_type>/feature-values',
    methods=['GET']
)
@jwt_required()
@decode_query_ids('read')
def get_mapobject_feature_values(experiment_id, object_type):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/mapobjects/(string:mapobject_type)/feature-values

        Get all feature values
        (:class:`FeatureValue.value <tmlib.models.feature.FeatureValue`)
        for object of the given
        :class:`MapobjectType <tmlib.models.mapobject.MapobjectType`
        as a *n*x*p* *CSV* table, where *n* is the number of
        mapobjects (:class:`Mapobject <tmlib.models.mapobject.Mapobject`) and
        *p* is the number of features
        (:class:`Feature <tmlib.models.feature.Feature>`).

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 400: malformed request
        :statuscode 401: unauthorized
        :statuscode 404: not found

    .. note:: The first row of the table are column (feature) names.
    """
    experiment_name = check_permissions(experiment_id)
    with tm.utils.ExperimentSession(experiment_id) as session:
        try:
            mapobject_type = session.query(tm.MapobjectType).\
                filter_by(name=object_type).\
                one()
        except NoResultFound:
            raise ResourceNotFoundError(
                tm.MapobjectType, {'object_type': object_type}
            )

        def generate_feature_matrix(mapobject_type_id):
            mapobjects = session.query(tm.Mapobject.id).\
                filter_by(mapobject_type_id=mapobject_type_id).\
                order_by(tm.Mapobject.id).\
                all()
            features = session.query(tm.Feature.id, tm.Feature.name).\
                filter_by(mapobject_type_id=mapobject_type_id).\
                order_by(tm.Feature.id).\
                all()
            feature_ids = [f.id for f in features]
            feature_names = [f.name for f in features]
            # First line of CSV are column names
            for i in range(-1, len(mapobjects)):
                if i < 0:
                    yield ','.join(feature_names) + '\n'
                else:
                    feature_values = session.query(tm.FeatureValue.value).\
                        filter(
                            tm.FeatureValue.mapobject_id == mapobjects[i].id,
                            tm.FeatureValue.feature_id.in_(feature_ids)
                        ).\
                        order_by(tm.FeatureValue.feature_id).\
                        all()
                    values = [str(f.value) for f in feature_values]
                    yield ','.join(values) + '\n'

        return Response(
            generate_feature_matrix(mapobject_type.id),
            mimetype='text/csv',
            headers={
                'Content-Disposition': 'attachment; filename=%s' % (
                    '%s_%s_feature-values.csv' % (experiment_name, object_type)
                )
            }
        )


@api.route(
    '/experiments/<experiment_id>/mapobjects/<object_type>/metadata',
    methods=['GET']
)
@jwt_required()
@decode_query_ids('read')
def get_mapobject_metadata(experiment_id, object_type):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/mapobjects/(string:mapobject_type)/metadata

        Get :class:`FeatureValue <tmlib.models.feature.FeatureValue` for
        the given :class:`MapobjectType <tmlib.models.mapobject.MapobjectType`
        as a *n*x*p* feature table, where *n* is the number of
        mapobjects (:class:`Mapobject <tmlib.models.mapobject.Mapobject`) and
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
    experiment_name = check_permissions(experiment_id)
    with tm.utils.ExperimentSession(experiment_id) as session:
        try:
            mapobject_type = session.query(tm.MapobjectType).\
                filter_by(name=object_type).\
                one()
        except NoResultFound:
            raise ResourceNotFoundError(
                tm.MapobjectType, {'object_type': object_type}
            )

        def generate_feature_matrix(mapobject_type_id):
            mapobjects = session.query(tm.Mapobject.id).\
                filter_by(mapobject_type_id=mapobject_type_id).\
                order_by(tm.Mapobject.id).\
                all()
            features = session.query(tm.Feature.id, tm.Feature.name).\
                filter_by(mapobject_type_id=mapobject_type_id).\
                order_by(tm.Feature.id).\
                all()
            feature_ids = [f.id for f in features]
            feature_names = [f.name for f in features]
            # First line of CSV are column names
            for i in range(-1, len(mapobjects)):
                if i < 0:
                    names = [
                        'label', 'tpoint', 'zplane',
                        'plate_name', 'well_name',
                        'site_y', 'site_x',
                    ]
                    yield ','.join(names) + '\n'
                else:
                    values = session.query(
                            tm.MapobjectSegmentation.label,
                            tm.MapobjectSegmentation.tpoint,
                            tm.MapobjectSegmentation.zplane,
                            tm.Plate.name,
                            tm.Well.name,
                            tm.Site.y,
                            tm.Site.x,
                        ).\
                        join(tm.Mapobject).\
                        join(tm.Site).\
                        join(tm.Well).\
                        join(tm.Plate).\
                        filter(tm.Mapobject.id == mapobjects[i].id).\
                        one()
                    values = [str(f) for f in values]
                    yield ','.join(values) + '\n'

        return Response(
            generate_feature_matrix(mapobject_type.id),
            mimetype='text/csv',
            headers={
                'Content-Disposition': 'attachment; filename=%s' % (
                    '%s_%s_metadata.csv' % (experiment_name, object_type)
                )
            }
        )

