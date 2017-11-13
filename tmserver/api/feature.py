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
from collections import OrderedDict
import csv
import json
import logging
import numpy as np
import pandas as pd
from cStringIO import StringIO
from flask_jwt import jwt_required
from flask import jsonify, request, send_file, Response, stream_with_context
from sqlalchemy.orm.exc import NoResultFound

import tmlib.models as tm

from tmserver.api import api
from tmserver.util import (
    decode_query_ids, assert_query_params, assert_form_params,
    is_true, is_false
)
from tmserver.error import *
from tmserver.api.mapobject import (
    _get_matching_sites, _get_matching_plates, _get_matching_wells,
    _get_matching_layers, _get_mapobjects_at_ref_position,
    _get_border_mapobjects_at_ref_position
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
    with tm.utils.ExperimentSession(experiment_id, False) as session:
        session.query(tm.FeatureValue.values.delete(str(feature_id)))
        session.query(tm.Feature).filter_by(id=feature_id).delete()
    return jsonify(message='ok')


@api.route(
    '/experiments/<experiment_id>/mapobject_types/<mapobject_type_id>/feature-values',
    methods=['POST']
)
@jwt_required()
@assert_form_params(
    'plate_name', 'well_name', 'well_pos_x', 'well_pos_y', 'tpoint',
    'names', 'values', 'labels'
)
@decode_query_ids('write')
def add_feature_values(experiment_id, mapobject_type_id):
    """
    .. http:post:: /api/experiments/(string:experiment_id)/mapobject_types/(string:mapobject_type_id)/feature-values

        Add :class:`FeatureValues <tmlib.models.feature.FeatureValues>`
        for every :class:`Mapobject <tmlib.models.mapobject.Mapobject>` of the
        given :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>` at a
        given :class:`Site <tmlib.models.site.Site>` and time point.
        Feature values must be provided in form of a *n*x*p* array, where
        *n* are the number of objects (rows) and *p* the number of features
        (columns). Rows are identifiable by *labels* and columns by *names*.
        Provided *labels* must match the
        :attr:`label <tmlib.models.mapobject.MapobjectSegmentation.label>` of
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
                "names": ["feature1", "feature2", "feature3"],
                "labels": [1, 2],
                "values" [
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

    feature_names = data.get('names')
    feature_values = data.get('values')
    labels = data.get('labels')

    try:
        data = pd.DataFrame(feature_values, columns=feature_names, index=labels)
    except Exception as err:
        logger.error(
            'feature values were not provided in correct format: %s', str(err)
        )
        raise ResourceNotFoundError(
            'Feature values were not provided in the correct format.'
        )

    with tm.utils.ExperimentSession(experiment_id) as session:
        feature_lut = dict()
        for name in data.columns:
            feature = session.get_or_create(
                tm.Feature, name=name, mapobject_type_id=mapobject_type_id
            )
            feature_lut[name] = str(feature.id)
        data.rename(feature_lut, inplace=True)

    with tm.utils.ExperimentSession(experiment_id) as session:
        site = session.query(tm.Site).\
            join(tm.Well).\
            join(tm.Plate).\
            filter(
                tm.Plate.name == plate_name, tm.Well.name == well_name,
                tm.Site.y == well_pos_y, tm.Site.x == well_pos_x
            ).\
            one()
        site_id = site.id

        layer = session.query(tm.SegmentationLayer.id).\
            filter_by(mapobject_type_id=mapobject_type_id, tpoint=tpoint).\
            first()
        layer_id = layer.id

        # This approach assumes that object segmentations have the same labels
        # across different z-planes.
        segmentations = session.query(
                tm.MapobjectSegmentation.mapobject_id,
                tm.MapobjectSegmentation.label
            ).\
            filter(
                tm.MapobjectSegmentation.partition_key == site_id,
                tm.MapobjectSegmentation.segmentation_layer_id == layer_id
            ).\
            all()
        if len(segmentations) == 0:
            raise ResourceNotFoundError(tm.MapobjectSegmentation)

    with tm.utils.ExperimentSession(experiment_id, False) as session:
        feature_values = list()
        for mapobject_id, label in segmentations:
            try:
                values = tm.FeatureValues(
                    partition_key=site_id, mapobject_id=mapobject_id,
                    values=data.loc[label], tpoint=tpoint
                )
            except IndexError:
                raise ResourceNotFoundError(
                    tm.MapobjectSegmentation, label=label
                )
            feature_values.append(values)
        session.bulk_ingest(feature_values)

    return jsonify(message='ok')


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
        mapobject_type_ref_type = mapobject_type.ref_type

    if mapobject_type_ref_type in {'Plate', 'Well'}:
        if well_pos_y is not None:
            raise MalformedRequestError(
                'Invalid query parameter "well_pos_y" for mapobjects of type '
                '"{0}"'.format(mapobject_type_name)
            )
        if well_pos_x is not None:
            raise MalformedRequestError(
                'Invalid query parameter "well_pos_x" for mapobjects of type '
                '"{0}"'.format(mapobject_type_name)
            )
        if mapobject_type_ref_type == 'Plate':
            if well_name is not None:
                raise MalformedRequestError(
                    'Invalid query parameter "well_name" for mapobjects of type '
                    '"{0}"'.format(mapobject_type_name)
                )

    filename_formatstring = '{experiment}'
    if plate_name is not None:
        filename_formatstring += '_{plate}'
    if well_name is not None:
        filename_formatstring += '_{well}'
    if well_pos_y is not None:
        filename_formatstring += '_y{y}'
    if well_pos_x is not None:
        filename_formatstring += '_x{x}'
    if tpoint is not None:
        filename_formatstring += '_t{t}'
    filename_formatstring += '_{object_type}_feature-values.csv'
    filename = filename_formatstring.format(
        experiment=experiment_name, plate=plate_name, well=well_name,
        y=well_pos_y, x=well_pos_x,
        t=tpoint, object_type=mapobject_type_name
    )

    def generate_feature_matrix(mapobject_type_id, ref_type):
        data = StringIO()
        w = csv.writer(data)

        with tm.utils.ExperimentSession(experiment_id) as session:

            results = _get_matching_layers(session, tpoint)
            layer_lut = dict()
            for r in results:
                layer_lut[r.id] = {'tpoint': r.tpoint, 'zplane': r.zplane}

            if ref_type == 'Plate':
                results = _get_matching_plates(session, plate_name)
            elif ref_type == 'Well':
                results = _get_matching_wells(session, plate_name, well_name)
            elif ref_type == 'Site':
                results = _get_matching_sites(
                    session, plate_name, well_name, well_pos_y, well_pos_x
                )
            ref_ids = [r.id for r in results]

            features = session.query(tm.Feature.name).\
                filter_by(mapobject_type_id=mapobject_type_id).\
                order_by(tm.Feature.id).\
                all()
            feature_names = [f.name for f in features]

            ref_mapobject_type = session.query(tm.MapobjectType.id).\
                filter_by(ref_type=ref_type, id=mapobject_type_id).\
                one()

        w.writerow(tuple(feature_names))
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)

        for ref_id in ref_ids:
            logger.debug('collect feature values for %s %d', ref_type, ref_id)
            with tm.utils.ExperimentSession(experiment_id) as session:
                mapobjects = _get_mapobjects_at_ref_position(
                    session, mapobject_type_id, ref_id, layer_lut.keys()
                )
                mapobject_ids = [m.id for m in mapobjects]

                if not mapobject_ids:
                    logger.warn(
                        'no mapobjects found for %s %d', ref_type, ref_id
                    )
                    continue

                feature_values = session.query(
                        tm.FeatureValues.mapobject_id, tm.FeatureValues.values
                    ).\
                    filter(tm.FeatureValues.mapobject_id.in_(mapobject_ids)).\
                    all()
                feature_values_lut = dict(feature_values)

                if not feature_values_lut:
                    logger.warn(
                        'no feature values found for %s %d', ref_type, ref_id
                    )
                    continue

                for mapobject_id, label, segmentation_layer_id in mapobjects:
                    if mapobject_id not in feature_values_lut:
                        logger.warn(
                            'no feature values found for mapobject %d',
                            mapobject_id
                        )
                        w.writerow(tuple(
                            [str(np.nan) for x in xrange(len(feature_names))]
                        ))
                        yield data.getvalue()
                        data.seek(0)
                        data.truncate(0)
                        continue

                    vals = feature_values_lut[mapobject_id]
                    # Values must be sorted based on feature_id, such that they
                    # end up in the correct column of the CSV table matching
                    # the corresponding column names.
                    # Feature IDs must be sorted as integers to get the
                    # desired order.
                    w.writerow(tuple([
                        vals[k] for k in sorted(vals, key=lambda k: int(k))
                    ]))
                yield data.getvalue()
                data.seek(0)
                data.truncate(0)

    return Response(
        generate_feature_matrix(mapobject_type_id, mapobject_type_ref_type),
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename={filename}'.format(
                filename=filename
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
        mapobject_type_ref_type = mapobject_type.ref_type

    if mapobject_type_ref_type in {'Plate', 'Well'}:
        if well_pos_y is not None:
            raise MalformedRequestError(
                'Invalid query parameter "well_pos_y" for mapobjects of type '
                '"{0}"'.format(mapobject_type_name)
            )
        if well_pos_x is not None:
            raise MalformedRequestError(
                'Invalid query parameter "well_pos_x" for mapobjects of type '
                '"{0}"'.format(mapobject_type_name)
            )
        if mapobject_type_ref_type == 'Plate':
            if well_name is not None:
                raise MalformedRequestError(
                    'Invalid query parameter "well_name" for mapobjects of type '
                    '"{0}"'.format(mapobject_type_name)
                )

    filename_formatstring = '{experiment}'
    if plate_name is not None:
        filename_formatstring += '_{plate}'
    if well_name is not None:
        filename_formatstring += '_{well}'
    if well_pos_y is not None:
        filename_formatstring += '_y{y}'
    if well_pos_x is not None:
        filename_formatstring += '_x{x}'
    if tpoint is not None:
        filename_formatstring += '_t{t}'
    filename_formatstring += '_{object_type}_metadata.csv'
    filename = filename_formatstring.format(
        experiment=experiment_name, plate=plate_name, well=well_name,
        y=well_pos_y, x=well_pos_x,
        t=tpoint, object_type=mapobject_type_name
    )

    def generate_feature_matrix(mapobject_type_id, ref_type):
        data = StringIO()
        w = csv.writer(data)

        with tm.utils.ExperimentSession(experiment_id) as session:

            results = _get_matching_layers(session, tpoint)
            layer_lut = dict()
            for r in results:
                layer_lut[r.id] = {'tpoint': r.tpoint, 'zplane': r.zplane}

            ref_position_lut = OrderedDict()
            if ref_type == 'Plate':
                results = _get_matching_plates(session, plate_name)
                for r in results:
                    ref_position_lut[r.id] = {
                        'plate_name': r.plate_name,
                    }
                metadata_names = [
                    'plate_name'
                ]
            elif ref_type == 'Well':
                results = _get_matching_wells(session, plate_name, well_name)
                for r in results:
                    ref_position_lut[r.id] = {
                        'plate_name': r.plate_name,
                        'well_name': r.well_name,
                    }
                metadata_names = [
                    'plate_name', 'well_name'
                ]
            elif ref_type == 'Site':
                results = _get_matching_sites(
                    session, plate_name, well_name, well_pos_y, well_pos_x
                )
                for r in results:
                    ref_position_lut[r.id] = {
                        'well_pos_y': r.well_pos_y,
                        'well_pos_x': r.well_pos_x,
                        'plate_name': r.plate_name,
                        'well_name': r.well_name,
                    }
                metadata_names = [
                    'plate_name', 'well_name', 'well_pos_y', 'well_pos_x',
                    'tpoint', 'zplane', 'label', 'is_border'
                ]

            tool_results = session.query(tm.ToolResult.id, tm.ToolResult.name).\
                filter_by(mapobject_type_id=mapobject_type_id).\
                order_by(tm.ToolResult.id).\
                all()
            tool_result_names = [t.name for t in tool_results]
            tool_result_ids = [t.id for t in tool_results]

            ref_mapobject_type = session.query(tm.MapobjectType.id).\
                filter_by(ref_type=ref_type).\
                order_by(tm.MapobjectType.id).\
                first()

        w.writerow(tuple(metadata_names + tool_result_names))
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)

        for ref_id in ref_position_lut:
            logger.debug('collect metadata for %s %d', ref_type, ref_id)
            with tm.utils.ExperimentSession(experiment_id) as session:
                mapobjects = _get_mapobjects_at_ref_position(
                    session, mapobject_type_id, ref_id, layer_lut.keys()
                )
                mapobject_ids = [m.id for m in mapobjects]

                if not mapobject_ids:
                    logger.warn(
                        'no mapobjects found for %s %d', ref_type, ref_id
                    )
                    continue

                if ref_type == 'Site':
                    border_segmentations = _get_border_mapobjects_at_ref_position(
                        session, mapobject_ids, ref_mapobject_type.id, ref_id
                    )
                    border_mapobject_ids = [
                        s.mapobject_id for s in border_segmentations
                    ]

                label_values = session.query(
                        tm.LabelValues.mapobject_id, tm.LabelValues.values
                    ).\
                    filter(tm.LabelValues.mapobject_id.in_(mapobject_ids)).\
                    all()
                label_values_lut = dict(label_values)

                warn = True
                if not label_values_lut:
                    warn = False

                rows = list()
                for mapobject_id, label, segmenation_layer_id in mapobjects:
                    metadata_values = [ref_position_lut[ref_id]['plate_name']]

                    if 'well_name' in ref_position_lut[ref_id]:
                        metadata_values.append(
                            ref_position_lut[ref_id]['well_name']
                        )

                    if 'well_pos_y' in ref_position_lut[ref_id]:
                        metadata_values.extend([
                            str(ref_position_lut[ref_id]['well_pos_y']),
                            str(ref_position_lut[ref_id]['well_pos_x']),
                        ])

                    if layer_lut[segmenation_layer_id]['tpoint'] is not None:
                        metadata_values.extend([
                            str(layer_lut[segmenation_layer_id]['tpoint']),
                            str(layer_lut[segmenation_layer_id]['zplane']),
                            str(label),
                            str(1 if mapobject_id in border_mapobject_ids else 0)
                        ])

                    if mapobject_id not in label_values_lut:
                        if warn:
                            logger.warn(
                                'no label values found for mapobject %d',
                                mapobject_id
                            )
                        metadata_values += [
                            str(np.nan) for x in xrange(len(tool_result_names))
                        ]
                    else:
                        vals = label_values_lut[mapobject_id]
                        tool_result_values = list()
                        for tid in tool_result_ids:
                            try:
                                v = vals[str(tid)]
                            except KeyError:
                                v = str(np.nan)
                            tool_result_values.append(v)
                        metadata_values += tool_result_values
                    w.writerow(tuple(metadata_values))
                yield data.getvalue()
                data.seek(0)
                data.truncate(0)

    return Response(
        generate_feature_matrix(mapobject_type_id, mapobject_type_ref_type),
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename={filename}'.format(
                filename=filename
            )
        }
    )
