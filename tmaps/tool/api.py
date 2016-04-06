import json

from flask import jsonify, request
from flask_jwt import jwt_required
from flask.ext.jwt import current_identity
from sqlalchemy.sql import text

from tmaps.mapobject import MapobjectOutline
from tmaps.extensions import db
from tmaps.tool import Tool, ToolSession
from tmaps.tool.result import LabelResult
from tmaps.api import api
from tmaps.experiment import Experiment
from tmaps.response import (
    MALFORMED_REQUEST_RESPONSE,
    RESOURCE_NOT_FOUND_RESPONSE,
    NOT_AUTHORIZED_RESPONSE
)


def _create_mapobject_feature(obj_id, geometry_obj):
    """Create a GeoJSON feature object given a object id of type int
    and a object that represents a GeoJSON geometry definition."""
    return {
        "type": "Feature",
        "geometry": geometry_obj,
        "properties": {
            "id": str(obj_id)
        }
    }


@api.route('/tools')
@jwt_required()
def get_tools():
    # TODO: Only return tools for the current user
    return jsonify({
        'tools': db.session.query(Tool).all()
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
    'data_storage'. Also, a h5 dataset can be retrieved via experiment instance
    property: 'self.experiment_dataset'.

    Returns:

    {
        return_value: object
    }

    """
    data = json.loads(request.data)

    # Check if the request is valid.
    if not 'payload' in data \
            or not 'experiment_id' in data \
            or not 'session_uuid' in data:
        return MALFORMED_REQUEST_RESPONSE

    payload = data.get('payload', {})
    session_uuid = data.get('session_uuid')
    experiment_id = data.get('experiment_id')

    # Check if the user has permissions to access this experiment.
    e = db.session.query(Experiment).get_with_hash(experiment_id)
    if e is None:
        return RESOURCE_NOT_FOUND_RESPONSE
    if not e.belongs_to(current_identity):
        return NOT_AUTHORIZED_RESPONSE

    # Instantiate the correct tool plugin class.
    tool = db.session.query(Tool).get_with_hash(tool_id)
    tool_cls = tool.get_class()
    tool_inst = tool_cls()

    # Load or create the persistent tool session.
    session = db.session.query(ToolSession).\
        filter_by(uuid=session_uuid).first()
    if session is None:
        session = ToolSession(
            experiment_id=e.id, uuid=session_uuid, tool_id=tool.id)
        db.session.add(session)
        db.session.commit()

    # Execute the tool plugin.
    tool_result = tool_inst.process_request(payload, session, e)

    response = {
        'result_type': tool_result.__class__.__name__,
        'payload': tool_result,
        'session_uuid': session_uuid,
        'tool_id': tool_id
    }

    return jsonify(response)



@api.route('/labelresults/<labelresult_id>', methods=['GET'])
def get_labelresult(labelresult_id):
    # The coordinates of the requested tile
    x = request.args.get('x')
    y = request.args.get('y')
    z = request.args.get('z')
    zlevel = request.args.get('zlevel')
    t = request.args.get('t')

    # Check arguments for validity and convert to integers
    if any([var is None for var in [x, y, z, zlevel, t]]):
        return MALFORMED_REQUEST_RESPONSE
    else:
        x, y, z, zlevel, t = map(int, [x, y, z, zlevel, t])

    label_result = db.session.query(LabelResult).get_with_hash(labelresult_id)

    query_res = label_result.mapobject_type.get_mapobject_outlines_within_tile(
        x, y, z, zplane=zlevel, tpoint=t)
    features = []

    if len(query_res) > 0:
        mapobject_ids = [c[0] for c in query_res]
        mapobject_id_to_label = label_result.get_labels_for_objects(mapobject_ids)

        for id, geom_geojson_str in query_res:
            feature = {
                "type": "Feature",
                "geometry": json.loads(geom_geojson_str),
                "properties": {
                    "label": mapobject_id_to_label[id],
                    "id": id
                }
            }
            features.append(feature)

    return jsonify({
        "type": "FeatureCollection",
        "features": features
    })
