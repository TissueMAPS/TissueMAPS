import json

from flask import jsonify, request
from flask_jwt import jwt_required
from flask.ext.jwt import current_identity
from sqlalchemy.sql import text

from tmaps.mapobject import MapobjectOutline
from tmaps.extensions.database import db
from tmaps.extensions.encrypt import decode
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
        'tools': [t.to_dict() for t in Tool.query.all()]
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
    e = Experiment.get(experiment_id)
    if e is None:
        return RESOURCE_NOT_FOUND_RESPONSE
    if not e.belongs_to(current_identity):
        return NOT_AUTHORIZED_RESPONSE

    # Instantiate the correct tool plugin class.
    tool = Tool.get(tool_id)
    tool_cls = tool.get_class()
    tool_inst = tool_cls()

    # Load or create the persistent tool session.
    session = ToolSession.query.filter_by(uuid=session_uuid).first()
    if session is None:
        session = ToolSession.create(
            experiment_id=e.id, user_id=current_identity.id,
            uuid=session_uuid, tool_id=tool.id, appstate_id=None)

    # Execute the tool plugin.
    tool_result = tool_inst.process_request(payload, session, e)

    response = {
        'result_type': tool_result.__class__.__name__,
        'payload': tool_result.to_dict(),
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

    label_result = LabelResult.get(int(labelresult_id))

    outlines = MapobjectOutline.get_mapobject_outlines_within_tile(
        label_result.mapobject_name, x, y, z, zlevel, t)
    features = []

    if len(outlines) > 0:
        n_points = sum([t[1] for t in outlines])
        mapobject_ids = [c[0] for c in outlines]
        mapobject_id_to_label = label_result.get_labels_for_objects(mapobject_ids)
        do_simplify_geom = n_points > 10000

        for id, n_points, poly_geojson, point_geojson in outlines:
            geom_geojson = point_geojson if do_simplify_geom else poly_geojson
            feature = {
                "type": "Feature",
                "geometry": json.loads(geom_geojson),
                "properties": {
                    "label": mapobject_id_to_label[id],
                    "id": id
                }
            }
            features.append(feature)

    return jsonify(
        {
            "type": "FeatureCollection",
            "features": features
        }
    )

# @api.route('/tools/<tool_id>/instances', methods=['POST'])
# @jwt_required()
# def create_tool_instance(tool_id):
#     """
#     The client opened a new tool window. Create a server-side
#     representation of that tool instance that allows the server to keep track
#     of what server-side tool data belongs to which appstate.
#     This method will be called by tissueMAPS itself whenever a window opens.

#     Request:

#     {
#         appstate_id: string,
#         experiment_id: string
#     }

#     Response:

#     {
#         'id': int,
#         'tool_id': string,
#         'appstate_id': int,
#         'experiment_id': int,
#         'user_id': int
#     }

#     Each subsequent request made from this tool window should use
#     `tool_instance_id` to identify itself. The framework will take care of this.
#     Doing so, the instances methods will have access to the saved data and other
#     required contextual info.

#     """
#     data = json.loads(request.data)
#     appstate_id = decode(data.get('appstate_id'))
#     experiment_id = decode(data.get('experiment_id'))

#     if not appstate_id or not experiment_id:
#         return 'Not a valid request', 400
#     else:
#         inst = ToolInstance(
#             tool_id=tool_id,
#             appstate_id=appstate_id,
#             experiment_id=experiment_id,
#             user_id=current_identity.id
#         )
#         db.session.add(inst)
#         db.session.commit()

#         return jsonify(inst.as_dict())


# @api.route('/tool_instances/<int:instance_id>', methods=['DELETE'])
# @jwt_required()
# def delete_toolinstance(instance_id):
#     inst = ToolInstance.query.get(instance_id)
#     if not inst:
#         return 'No ToolInstance found with id %d' % instance_id, 404
#     if inst.appstate.is_editable_by_user(current_identity):
#         db.session.delete(inst)
#         db.session.commit()
#         return 'ToolInstance was removed successfully', 200
#     else:
#         return 'You don\'t have the permission to edit the appstate, to ' \
#                'which this ToolInstance belongs', 401
