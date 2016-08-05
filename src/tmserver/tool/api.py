import json
import logging
from flask import jsonify, request, current_app
from flask_jwt import jwt_required
from flask.ext.jwt import current_identity

import tmlib.models as tm

from tmserver.extensions import db
from tmserver.tool import Tool, ToolSession, LabelLayer, LabelLayerLabel
from tmserver.api import api
from tmserver.experiment import Experiment
from tmserver.error import (
    MalformedRequestError,
    ResourceNotFoundError,
    NotAuthorizedError
)
from tmserver.util import extract_model_from_path, assert_request_params

logger = logging.getLogger(__name__)


def _create_mapobject_feature(obj_id, geometry_obj):
    """Create a GeoJSON feature object given a object id of type int
    and a object that represents a GeoJSON geometry definition."""
    return {
        'type': 'Feature',
        'geometry': geometry_obj,
        'properties': {
            'id': str(obj_id)
        }
    }


@api.route('/tools')
@jwt_required()
def get_tools():
    # TODO: Only return tools for the current user
    return jsonify({
        'data': db.session.query(Tool).all()
    })


@api.route(
    '/experiments/<experiment_id>/tools/<tool_id>/request',
    methods=['POST']
)
@jwt_required()
@assert_request_params('payload', 'session_uuid')
@extract_model_from_path(tm.Experiment, Tool, check_ownership=True)
def process_tool_request(experiment, tool):
    """
    Process a generic tool request sent by the client.
    POST payload should have the format:

    {
        experiment_id: string,
        payload: dict
    }

    The server searches for the Tool with id `tool_id` and call its
    request method passing it the argument `payload` as well as the tool
    instance object that was saved in the database when the window was opened on
    the client.
    The tool has access to trans-request storage via the instance property
    'data_storage'.

    Returns:

    {
        return_value: object
    }

    """
    logger.info('process tool request')
    data = request.get_json()

    payload = data.get('payload', {})
    session_uuid = data.get('session_uuid')

    # Instantiate the correct tool plugin class.
    tool_cls = tool.get_class()
    tool_inst = tool_cls()

    # Load or create the persistent tool session.
    session = db.session.query(ToolSession).\
        filter_by(uuid=session_uuid).\
        one_or_none()
    if session is None:
        session = ToolSession(
            experiment_id=experiment.id, uuid=session_uuid, tool_id=tool.id
        )
        db.session.add(session)
        db.session.commit()

    # Execute the tool plugin.
    use_spark = current_app.config.get('USE_SPARK', False)
    tool_result = tool_inst.process_request(
        payload, session, experiment, use_spark=use_spark
    )
    # Commit all results that may have been added to the db
    db.session.commit()

    response = {
        'result': tool_result,
        'session_uuid': session_uuid,
        'tool_id': tool_id
    }

    return jsonify(response)


@api.route(
    '/experiments/<experiment_id>/labellayers/<label_layer_id>/tiles',
    methods=['GET']
)
@assert_request_params('x', 'y', 'z', 'zplane', 'tpoint')
@extract_model_from_path(tm.Experiment, LabelLayer)
def get_result_labels(experiment, label_layer):
    """Get all mapobjects together with the labels that were assigned to them
    for a given tool result and tile coordinate.

    """
    logger.info('get result tiles for label layer "%s"', label_layer.type)
    # The coordinates of the requested tile
    x = request.args.get('x', type=int)
    y = request.args.get('y', type=int)
    z = request.args.get('z', type=int)
    zplane = request.args.get('zplane', type=int)
    tpoint = request.args.get('tpoint', type=int)

    mapobject_type = db.session.query(tm.MapobjectType).\
        get(label_layer.mapobject_type_id)
    query_res = mapobject_type.get_mapobject_outlines_within_tile(
        x, y, z, zplane=zplane, tpoint=tpoint
    )

    features = []
    has_mapobjects_within_tile = len(query_res) > 0

    if has_mapobjects_within_tile:
        mapobject_ids = [c[0] for c in query_res]
        mapobject_id_to_label = label_layer.get_labels_for_objects(mapobject_ids)

        features = [
            {
                'type': 'Feature',
                'geometry': json.loads(geom_geojson_str),
                'properties': {
                    'label': mapobject_id_to_label[id],
                    'id': id
                 }
            }
            for id, geom_geojson_str in query_res
        ]

    return jsonify({
        'type': 'FeatureCollection',
        'features': features
    })
