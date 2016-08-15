import json
import logging
from flask import jsonify, request, current_app
from flask_jwt import jwt_required
from flask.ext.jwt import current_identity

import tmlib.models as tm

from tmserver.tool import ToolSession, LabelLayer, LabelLayerValue
from tmserver.api import api
from tmserver.error import (
    MalformedRequestError,
    ResourceNotFoundError,
    NotAuthorizedError
)
from tmserver.util import decode_url_ids, decode_body_ids, assert_request_params
from tmserver.toolbox import SUPPORTED_TOOLS
from tmserver.toolbox import get_tool_class


logger = logging.getLogger(__name__)


def _create_mapobject_feature(mapobject_id, geometry_description):
    """Creates a GeoJSON feature for the given mapobject and GeoJSON geometry.

    Parameters
    ----------
    mapobject_id: int
        ID of the mapobject
    geometry_description: XXX
        description of a GeoJSON geometry

    Returns
    -------
    dict
    """
    return {
        'type': 'Feature',
        'geometry': geometry_description,
        'properties': {
            'id': str(mapobject_id)
        }
    }


@api.route('/tools', methods=['GET'])
@jwt_required()
def get_tools():
    tool_descriptions = list()
    for name in SUPPORTED_TOOLS:
        tool_cls = get_tool_class(name)
        tool_descriptions.append({
            'name': tool_cls.__name__,
            'icon': tool_cls.__icon__,
            'description': tool_cls.__description__,
            'methods': getattr(tool_cls, '__methods__', [])
        })
    return jsonify(data=tool_descriptions)


@api.route(
    '/experiments/<experiment_id>/tools/request', methods=['POST']
)
@jwt_required()
@decode_url_ids()
@assert_request_params('payload', 'session_uuid', 'tool_name')
def process_tool_request(experiment_id, tool_name):
    """Processes a generic tool request sent by the client.
    POST payload should have the format:

    {
        payload: dict,
        session_uuid: str
    }

    Returns:

    {
        return_value: object
    }

    """
    data = request.get_json()
    payload = data.get('payload', {})
    session_uuid = data.get('session_uuid')
    tool_name = data.get('tool_name')

    # Instantiate the correct tool plugin class.
    logger.info('process request of tool "%s"', tool_name)
    tool_cls = get_tool_class(tool_name)
    tool = tool_cls()

    with tm.utils.ExperimentSession(experiment_id) as session:

        # Load or create the persistent tool session
        tool_session = session.get_or_create(ToolSession, uuid=session_uuid)

        # Execute the tool plugin.
        use_spark = current_app.config.get('USE_SPARK', False)
        tool_result = tool.process_request(
            payload, tool_session.id, use_spark=use_spark
        )

        return jsonify({
            'result': tool_result,
            'session_uuid': session_uuid
        })


@api.route(
    '/experiments/<experiment_id>/labellayers/<label_layer_id>/tiles',
    methods=['GET']
)
@decode_url_ids()
@assert_request_params('x', 'y', 'z', 'zplane', 'tpoint')
def get_result_labels(experiment_id, label_layer_id):
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

    with tm.utils.ExperimentSession(experiment_id) as session:
        mapobject_type = session.query(tm.MapobjectType).\
            get(label_layer.mapobject_type_id)
        query_res = mapobject_type.get_mapobject_outlines_within_tile(
            x, y, z, zplane=zplane, tpoint=tpoint
        )

        features = []
        has_mapobjects_within_tile = len(query_res) > 0

        if has_mapobjects_within_tile:
            mapobject_ids = [c[0] for c in query_res]
            mapobject_id_to_label = label_layer.get_labels_for_objects(
                mapobject_ids
            )

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

@api.route(
    '/experiments/<experiment_id>/toolresults/<toolresult_id>', methods=['GET']
)
@jwt_required()
@decode_url_ids()
def get_tool_result(experiment_id, toolresult_id):
    with tm.utils.ExperimentSession(experiment_id) as session:
        tool_result = session.query(tm.ToolResult).get(toolresult_id)
        return jsonify(tool_result)

