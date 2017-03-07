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
from tmserver.error import *


logger = logging.getLogger(__name__)

def _get_matching_sites(session, plate_name, well_name, well_pos_y, well_pos_x):
    query = session.query(
            tm.Site.id,
            tm.Site.y.label('well_pos_y'),
            tm.Site.x.label('well_pos_x'),
            tm.Well.name.label('well_name'),
            tm.Plate.name.label('plate_name')
        ).\
        join(tm.Well).\
        join(tm.Plate)
    if plate_name is not None:
        logger.debug('filter metadata by plate "%s"', plate_name)
        results = session.query(tm.Plate.id).\
            filter_by(name=plate_name).\
            count()
        if results == 0:
            raise ResourceNotFoundError(tm.Plate, name=plate_name)
        query = query.filter(tm.Plate.name == plate_name)
    if well_name is not None:
        logger.debug('filter metadata by well "%s"', well_name)
        results = session.query(tm.Well.id).\
            filter_by(name=well_name).\
            count()
        if results == 0:
            raise ResourceNotFoundError(tm.Well, name=well_name)
        query = query.filter(tm.Well.name == well_name)
    if well_pos_y is not None:
        logger.debug(
            'filter metadata by well position y %d', well_pos_y
        )
        results = session.query(tm.Site.id).\
            filter_by(y=well_pos_y).\
            count()
        if results == 0:
            raise ResourceNotFoundError(tm.Site, y=well_pos_y)
        query = query.filter(tm.Site.y == well_pos_y)
    if well_pos_x is not None:
        logger.debug(
            'filter metadata by well position x %d', well_pos_x
        )
        results = session.query(tm.Site.id).\
            filter_by(x=well_pos_x).\
            count()
        if results == 0:
            raise ResourceNotFoundError(tm.Site, x=well_pos_x)
        query = query.filter(tm.Site.x == well_pos_x)
    return query.order_by(tm.Site.id).all()


def _get_matching_layers(session, tpoint):
    query = session.query(tm.SegmentationLayer)
    if tpoint is not None:
        logger.debug('filter feature values by tpoint %d', tpoint)
        results = session.query(tm.SegmentationLayer.id).\
            filter_by(tpoint=tpoint).\
            count()
        if results == 0:
            raise ResourceNotFoundError(tm.SegmentationLayer, tpoint=tpoint)
        query = query.filter(tm.SegmentationLayer.tpoint == tpoint)
    return query.all()


def _get_mapobjects_per_site(session, mapobject_type_id, site_mapobject_type_id,
        site_id, segmentation_layer_ids):
        try:
            site_segmentation = session.query(
                    tm.MapobjectSegmentation.geom_polygon
                ).\
                join(tm.Mapobject).\
                filter(
                    tm.Mapobject.ref_id == site_id,
                    tm.Mapobject.mapobject_type_id == site_mapobject_type_id
                ).\
                one()
        except NoResultFound:
            raise ResourceNotFound(
                tm.Mapobject, ref_id=site_id,
                mapobject_type_id=mapobject_type_id
            )

        return session.query(
                tm.Mapobject.id, tm.MapobjectSegmentation.label,
                tm.MapobjectSegmentation.segmentation_layer_id
            ).\
            join(tm.MapobjectSegmentation).\
            filter(
                tm.Mapobject.mapobject_type_id == mapobject_type_id,
                tm.MapobjectSegmentation.geom_polygon.ST_Intersects(
                    site_segmentation.geom_polygon
                ),
                tm.MapobjectSegmentation.segmentation_layer_id.in_(
                    segmentation_layer_ids
                )
            ).\
            order_by(tm.Mapobject.id).\
            all()


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
@assert_query_params(
    'plate_name', 'well_name', 'well_pos_x', 'well_pos_y', 'zplane', 'tpoint'
)
@decode_query_ids('read')
def get_segmentation_image(experiment_id, mapobject_type_name):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/mapobjects/(string:mapobject_type_name)/segmentations

        Get the segmentation image at a specified coordinate.

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 400: malformed request

        :query plate_name: name of the plate (required)
        :query well_name: name of the well (required)
        :query well_pos_x: x-coordinate of the site within the well (required)
        :query well_pos_y: y-coordinate of the site within the well (required)
        :query tpoint: time point (required)
        :query zplane: z-plane (required)

    """
    plate_name = request.args.get('plate_name')
    well_name = request.args.get('well_name')
    well_pos_x = request.args.get('well_pos_x', type=int)
    well_pos_y = request.args.get('well_pos_y', type=int)
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
                tm.Site.x == well_pos_x, tm.Site.y == well_pos_y
            ).\
            one()
        mapobject_type = session.query(tm.MapobjectType).\
            filter_by(name=mapobject_type_name).\
            one()
        # TODO
        polygons = mapobject_type.get_segmentations_per_site(
            site_id, tpoints=[tpoint], zplanes=[zplane]
        )
        if len(polygons) == 0:
            raise ResourceNotFoundError(tm.MapobjectSegmentation, request.args)

        y_offset, x_offset = site.aligned_offset
        height = site.aligned_height
        width = site.aligned_width

        filename = '%s_%s_x%.3d_y%.3d_z%.3d_t%.3d_%s.png' % (
            experiment_name, site.well.name, site.x, site.y, zplane, tpoint,
            mapobject_type_name
        )

    img = SegmentationImage.create_from_polygons(
        polygons[0][0], y_offset, x_offset, (height, width)
    )
    f = StringIO()
    f.write(img.png_encode())
    f.seek(0)
    return send_file(
        f, attachment_filename=secure_filename(filename),
        mimetype='image/png', as_attachment=True
    )


@api.route(
    '/experiments/<experiment_id>/mapobjects/<mapobject_type_name>/feature-values',
    methods=['GET']
)
@jwt_required()
@decode_query_ids('read')
def get_feature_values(experiment_id, mapobject_type_name):
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

        :query plate_name: name of the plate (optional)
        :query well_name: name of the well (optional)
        :query well_pos_x: x-coordinate of the site within the well (optional)
        :query well_pos_y: y-coordinate of the site within the well (optional)
        :query tpoint: time point (optional)

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 400: malformed request
        :statuscode 401: unauthorized
        :statuscode 404: not found

    .. note:: The table is send in form of a *CSV* stream with the first row
        representing column names.
    """
    plate_name = request.args.get('plate_name')
    well_name = request.args.get('well_name')
    well_pos_x = request.args.get('well_pos_x', type=int)
    well_pos_y = request.args.get('well_pos_y', type=int)
    tpoint = request.args.get('tpoint', type=int)

    with tm.utils.MainSession() as session:
        experiment = session.query(tm.ExperimentReference).get(experiment_id)
        experiment_name = experiment.name

    with tm.utils.ExperimentSession(experiment_id) as session:
        mapobject_type = session.query(tm.MapobjectType).\
            filter_by(name=mapobject_type_name).\
            one()
        mapobject_type_id = mapobject_type.id

    def generate_feature_matrix(mapobject_type_id):
        with tm.utils.ExperimentSession(experiment_id) as session:

            results = _get_matching_layers(session, tpoint)
            layer_lookup = dict()
            for record in results:
                layer_lookup[record.id] = {
                    'tpoint': record.tpoint, 'zplane': record.zplane
                }

            results = _get_matching_sites(
                session, plate_name, well_name, well_pos_y, well_pos_x
            )
            site_lookup = dict()
            for record in results:
                site_lookup[record.id] = {
                    'well_pos_y': record.well_pos_y,
                    'well_pos_x': record.well_pos_x,
                    'plate_name': record.plate_name,
                    'well_name': record.well_name,
                }

            features = session.query(tm.Feature.name).\
                filter_by(mapobject_type_id=mapobject_type_id).\
                order_by(tm.Feature.id).\
                all()
            feature_names = [f.name for f in features]

            yield ','.join(feature_names) + '\n'
            site_mapobject_type = session.query(tm.MapobjectType.id).\
                filter_by(ref_type=tm.Site.__name__).\
                one()
            for site_id in site_lookup:
                results = _get_mapobjects_per_site(
                    session, mapobject_type_id, site_mapobject_type.id,
                    site_id, layer_lookup.keys()
                        )
                for mapobject_id, label, segmenation_layer_id in results:
                    # One could nicely filter features values using slice()
                    feature_values = session.query(tm.FeatureValues.values).\
                        filter_by(mapobject_id=mapobject_id).\
                        one()
                    values = feature_values.values
                    # The keys in a dictionary don't have any order.
                    # Values must be sorted based on feature_id, such that they
                    # end up in the correct column of the CSV table matching
                    # the corresponding column names.
                    values = [values[k] for k in sorted(values)]
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
def get_metadata(experiment_id, mapobject_type_name):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/mapobjects/(string:mapobject_type_name)/metadata

        Get positional information for
        the given :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`
        as a *n*x*p* feature table, where *n* is the number of
        mapobjects (:class:`Mapobject <tmlib.models.mapobject.Mapobject>`) and
        *p* is the number of metadata attributes.

        :query plate_name: name of the plate (optional)
        :query well_name: name of the well (optional)
        :query well_pos_x: x-coordinate of the site within the well (optional)
        :query well_pos_y: y-coordinate of the site within the well (optional)
        :query tpoint: time point (optional)

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 400: malformed request
        :statuscode 401: unauthorized
        :statuscode 404: not found

    .. note:: The table is send in form of a *CSV* stream with the first row
        representing column names.
    """
    plate_name = request.args.get('plate_name')
    well_name = request.args.get('well_name')
    well_pos_x = request.args.get('well_pos_x', type=int)
    well_pos_y = request.args.get('well_pos_y', type=int)
    tpoint = request.args.get('tpoint', type=int)

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

            results = _get_matching_layers(session, tpoint)
            layer_lookup = dict()
            for record in results:
                layer_lookup[record.id] = {
                    'tpoint': record.tpoint, 'zplane': record.zplane
                }

            results = _get_matching_sites(
                session, plate_name, well_name, well_pos_y, well_pos_x
            )
            site_lookup = dict()
            for record in results:
                site_lookup[record.id] = {
                    'well_pos_y': record.well_pos_y,
                    'well_pos_x': record.well_pos_x,
                    'plate_name': record.plate_name,
                    'well_name': record.well_name,
                }

            names = [
                'plate_name', 'well_name', 'well_pos_y', 'well_pos_x',
                'tpoint', 'zplane', 'label'
            ]
            yield ','.join(names) + '\n'
            site_mapobject_type = session.query(tm.MapobjectType.id).\
                filter_by(ref_type=tm.Site.__name__).\
                one()
            for site_id in site_lookup:
                results = _get_mapobjects_per_site(
                    session, mapobject_type_id, site_mapobject_type.id,
                    site_id, layer_lookup.keys()
                )
                for mapobject_id, label, segmenation_layer_id in results:
                    values = [
                        site_lookup[site_id]['plate_name'],
                        site_lookup[site_id]['well_name'],
                        str(site_lookup[site_id]['well_pos_y']),
                        str(site_lookup[site_id]['well_pos_x']),
                        str(layer_lookup[segmenation_layer_id]['tpoint']),
                        str(layer_lookup[segmenation_layer_id]['zplane']),
                        str(label)
                    ]
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

