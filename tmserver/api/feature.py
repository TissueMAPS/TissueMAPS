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
"""API view functions for querying :mod:`feature <tmlib.models.feature>`
resources.
"""
import json
import logging
import numpy as np
import pandas as pd
from flask_jwt import jwt_required
from flask import jsonify, request, send_file, Response
from sqlalchemy.orm.exc import NoResultFound

import tmlib.models as tm

from tmserver.api import api
from tmserver.util import (
    decode_query_ids, assert_query_params, assert_form_params,
    is_true, is_false
)
from tmserver.error import *
from tmserver.api.mapobject import (
    _get_matching_sites, _get_matching_layers, _get_mapobjects_at_site,
    _get_border_mapobjects_at_site
)


logger = logging.getLogger(__name__)


@api.route(
    '/experiments/<experiment_id>/features/<feature_id>',
    methods=['PUT']
)
@jwt_required()
@assert_form_params('name')
@decode_query_ids('read')
def update_feature(experiment_id, feature_id):
    """
    .. http:put:: /api/experiments/(string:experiment_id)/features/(string:feature_id)

        Update a :class:`Feature <tmlib.models.feature.Feature>`.

        **Example request**:

        .. sourcecode:: http

            Content-Type: application/json

            {
                "name": "New Name"
            }

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "message": "ok"
            }

        :statuscode 400: malformed request
        :statuscode 200: no error

    """
    data = request.get_json()
    name = data.get('name')
    logger.info('rename feature %d of experiment %d', feature_id, experiment_id)
    with tm.utils.ExperimentSession(experiment_id) as session:
        feature = session.query(tm.Feature).get(feature_id)
        feature.name = name
    return jsonify(message='ok')


@api.route(
    '/experiments/<experiment_id>/features/<feature_id>', methods=['DELETE']
)
@jwt_required()
@decode_query_ids('write')
def delete_feature(experiment_id, feature_id):
    """
    .. http:delete:: /api/experiments/(string:experiment_id)/features/(string:feature_id)

        Delete a specific :class:`Feature <tmlib.models.feature.Feature>`.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: application/json

            {
                "message": "ok"
            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 401: not authorized

    """
    logger.info('delete feature %d of experiment %d', feature_id, experiment_id)
    with tm.utils.ExperimentConnection(experiment_id) as connection:
        tm.Feature.delete_cascade(connection, id=feature_id)
    return jsonify(message='ok')


@api.route(
    '/experiments/<experiment_id>/mapobject_types/<mapobject_type_id>/feature-values',
    methods=['POST']
)
@jwt_required()
@assert_form_params(
    'plate_name'
)
@decode_query_ids('write')
def add_feature_values(experiment_id, mapobject_type_id):
    """
    .. http:post:: /api/experiments/(string:experiment_id)/mapobject_types/(string:mapobject_type_id)/feature-values

        Add :class:`FeatureValues <tmlib.models.feature.FeatureValues>`
        for every :class:`Mapobject <tmlib.models.mapobject.Mapobject>` of the
        given :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>` at a
        given time point :class:`Site <tmlib.models.site.Site>`.
        Feature values must be provided in form of a *n*x*p* array, where
        *n* are the number of objects (rows) and *p* the number of features
        (columns). Rows are identifiable by *segmentation_labels* and columns
        by *feature_names*. The provided *segmentation_labels* must match the
        :attr:`labels <tmlib.models.mapobject.MapobjectSegmentation.label>` of
        segmented objects.

        **Example request**:

        .. sourcecode:: http

            Content-Type: application/json

            {
                "plate_name": "plate1",
                "well_name": "D04",
                "well_pos_y": 0,
                "well_pos_x": 2,
                "tpoint": 0
                "feature_names": ["feature1", "feature2", "feature3"],
                "segmentation_labels": [1, 2],
                "feature_values" [
                    [2.45, 8.83, 4.37],
                    [5.67, 7.21, 1.58]
                ]
            }

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 400: malformed request
        :statuscode 401: unauthorized
        :statuscode 404: not found

    """
    data = request.get_json()

    plate_name = data.get('plate_name')
    well_name = data.get('well_name')
    well_pos_x = int(data.get('well_pos_x'))
    well_pos_y = int(data.get('well_pos_y'))
    tpoint = int(data.get('tpoint'))

    feature_names = data.get('feature_names')
    feature_values = data.get('feature_values')
    mapobject_segmentation_labels = data.get('segmentation_labels')

    try:
        data = pd.DataFrame(
            feature_values, columns=feature_names,
            index=mapobject_segmenation_labels
        )
    except Exception as err:
        logger.error('feature values where provided incorrectly: %s', str(err))
        raise ResourceNotFoundError(
            'Feature values were not provided in the correct format.'
        )

    with tm.utils.ExperimentSession(experiment_id) as session:
        feature_lut = dict()
        for name in data.columns:
            feature = session.get_or_create(
                tm.Feature,
                name=name, mapobject_type_id=mapobject_type_id
            )
            feature_lut[name] = str(feature.id)

    with tm.utils.ExperimentSession(experiment_id) as session:
        results = _get_matching_sites(
            session, plate_name, well_name, well_pos_y, well_pos_x
        )
        site_ids = [record.id for record in results]
        if len(sites) == 0:
            raise ResourceNotFoundError(tm.Site)
        else:
            site_id = sites[0].id

        segmentation_layers = _get_matching_layers(session, tpoint)
        segmentation_layer_ids = [s.id for s in segmentation_layers]

        mapobjects = _get_mapobjects_at_site(
            session, mapobject_type_id, site_mapobject_type.id,
            site_id, segmentation_layer_ids
        )
        if len(mapobjects) == 0:
            raise ResourceNotFoundError(tm.MapobjectSegmentation)

    with tm.utils.ExperimentConnection(experiment_id) as connection:
        for mapobject_id, label, segmenation_layer_id in mapobjects:
            try:
                values = data.iloc[label]
            except IndexError as err:
                raise ResourceNotFoundError(
                    'No segmented object found for label {0}.'.format(label)
                )
            values.rename(feature_lut, inplace=True)
            tm.FeatureValues.add(connection, values, mapobject_id, tpoint)


@api.route(
    '/experiments/<experiment_id>/mapobject_types/<mapobject_type_id>/feature-values',
    methods=['GET']
)
@jwt_required()
@decode_query_ids('read')
def get_feature_values(experiment_id, mapobject_type_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/mapobject_types/(string:mapobject_type_id)/feature-values

        Get :class:`FeatureValues <tmlib.models.feature.FeatureValues>`
        for objects of the given
        :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`
        in form of a *CSV* table with a row for each
        :class:`Mapobject <tmlib.models.mapobject.Mapobject>` and
        a column for each :class:`Feature <tmlib.models.feature.Feature>`.

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
            get(mapobject_type_id)
        mapobject_type_name = mapobject_type.name

    def generate_feature_matrix(mapobject_type_id):
        with tm.utils.ExperimentSession(experiment_id) as session:

            results = _get_matching_layers(session, tpoint)
            layer_lut = dict()
            for record in results:
                layer_lut[record.id] = {
                    'tpoint': record.tpoint, 'zplane': record.zplane
                }

            results = _get_matching_sites(
                session, plate_name, well_name, well_pos_y, well_pos_x
            )
            site_ids = [record.id for record in results]

            features = session.query(tm.Feature.name).\
                filter_by(mapobject_type_id=mapobject_type_id).\
                order_by(tm.Feature.id).\
                all()
            feature_names = [f.name for f in features]

            yield ','.join(feature_names) + '\n'
            site_mapobject_type = session.query(tm.MapobjectType.id).\
                filter_by(ref_type=tm.Site.__name__).\
                one()
            for site_id in site_ids:
                results = _get_mapobjects_at_site(
                    session, mapobject_type_id, site_mapobject_type.id,
                    site_id, layer_lut.keys()
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
    '/experiments/<experiment_id>/mapobject_types/<mapobject_type_id>/metadata',
    methods=['GET']
)
@jwt_required()
@decode_query_ids('read')
def get_metadata(experiment_id, mapobject_type_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/mapobject_types/(string:mapobject_type_id)/metadata

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
        mapobject_type = session.query(tm.MapobjectType).\
            get(mapobject_type_id)
        mapobject_type_name = mapobject_type.name

    def generate_feature_matrix(mapobject_type_id):
        with tm.utils.ExperimentSession(experiment_id) as session:

            results = _get_matching_layers(session, tpoint)
            layer_lut = dict()
            for record in results:
                layer_lut[record.id] = {
                    'tpoint': record.tpoint, 'zplane': record.zplane
                }

            results = _get_matching_sites(
                session, plate_name, well_name, well_pos_y, well_pos_x
            )
            site_lut = dict()
            for record in results:
                site_lut[record.id] = {
                    'well_pos_y': record.well_pos_y,
                    'well_pos_x': record.well_pos_x,
                    'plate_name': record.plate_name,
                    'well_name': record.well_name,
                }

            names = [
                'plate_name', 'well_name', 'well_pos_y', 'well_pos_x',
                'tpoint', 'zplane', 'label', 'is_border'
            ]
            yield ','.join(names) + '\n'
            site_mapobject_type = session.query(tm.MapobjectType.id).\
                filter_by(ref_type=tm.Site.__name__).\
                one()
            for site_id in site_lut:
                mapobjects = _get_mapobjects_at_site(
                    session, mapobject_type_id, site_mapobject_type.id,
                    site_id, layer_lut.keys()
                )
                mapobject_ids = [m.id for m in mapobjects]
                border_segmentations = _get_border_mapobjects_at_site(
                    session, mapobject_ids, site_mapobject_type.id, site_id
                )
                border_mapobject_ids = [
                    s.mapobject_id for s in border_segmentations
                ]
                for mapobject_id, label, segmenation_layer_id in mapobjects:
                    values = [
                        site_lut[site_id]['plate_name'],
                        site_lut[site_id]['well_name'],
                        str(site_lut[site_id]['well_pos_y']),
                        str(site_lut[site_id]['well_pos_x']),
                        str(layer_lut[segmenation_layer_id]['tpoint']),
                        str(layer_lut[segmenation_layer_id]['zplane']),
                        str(label),
                        str(1 if mapobject_id in border_mapobject_ids else 0)
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

