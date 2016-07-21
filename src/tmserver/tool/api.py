import json
import logging
from flask import jsonify, request, current_app
from flask_jwt import jwt_required
from flask.ext.jwt import current_identity

from tmserver.extensions import db
from tmserver.tool import Tool, ToolSession, LabelLayer, LabelLayerLabel
from tmserver.api import api
from tmserver.experiment import Experiment
from tmserver.error import (
    MalformedRequestError,
    ResourceNotFoundError,
    NotAuthorizedError
)
from tmserver.util import (
    extract_model_from_path,
    extract_model_from_body
)
from tmlib.models import MapobjectType

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


@api.route('/tools/<tool_id>/request', methods=['POST'])
@jwt_required()
def process_tool_request(tool_id):
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
    data = json.loads(request.data)

    # Check if the request is valid.
    if not 'payload' in data \
            or not 'experiment_id' in data \
            or not 'session_uuid' in data:
        raise MalformedRequestError()

    payload = data.get('payload', {})
    session_uuid = data.get('session_uuid')
    experiment_id = data.get('experiment_id')

    # Check if the user has permissions to access this experiment.
    e = db.session.query(Experiment).get_with_hash(experiment_id)
    if e is None:
        raise ResourceNotFoundError('No such experiment')
    if not e.belongs_to(current_identity):
        raise NotAuthorizedError()

    # Instantiate the correct tool plugin class.
    tool = db.session.query(Tool).get_with_hash(tool_id)
    tool_cls = tool.get_class()
    tool_inst = tool_cls()

    # Load or create the persistent tool session.
    session = db.session.query(ToolSession).\
        filter_by(uuid=session_uuid).\
        one_or_none()
    if session is None:
        session = ToolSession(
            experiment_id=e.id, uuid=session_uuid, tool_id=tool.id
        )
        db.session.add(session)
        db.session.commit()

    # Execute the tool plugin.
    use_spark = current_app.config.get('USE_SPARK', False)
    tool_result = tool_inst.process_request(payload, session, e, use_spark=use_spark)
    # Commit all results that may have been added to the db
    db.session.commit()

    response = {
        'result': tool_result,
        'session_uuid': session_uuid,
        'tool_id': tool_id
    }

    return jsonify(response)


@api.route('/labellayers/<label_layer_id>/tiles', methods=['GET'])
@extract_model_from_path(LabelLayer)
def get_result_labels(label_layer):
    """Get all mapobjects together with the labels that were assigned to them
    for a given tool result and tile coordinate.

    """
    logger.info('get result tiles for label layer "%s"', label_layer.type)
    # The coordinates of the requested tile
    x = request.args.get('x')
    y = request.args.get('y')
    z = request.args.get('z')
    zlevel = request.args.get('zplane')
    t = request.args.get('tpoint')

    # Check arguments for validity and convert to integers
    if any([var is None for var in [x, y, z, zplane, tpoint]]):
        raise MalformedRequestError(
            'One of the following request arguments is missing: '
            'x, t, z, zlevel, t'
        )
    else:
        x, y, z, zplane, tpoint = map(int, [x, y, z, zplane, tpoint])

    mapobject_type = db.session.query(MapobjectType).\
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
