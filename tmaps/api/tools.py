import json

from flask import jsonify, request
from flask_jwt import jwt_required
from flask.ext.jwt import current_identity

from tmaps.extensions.database import db
from tmaps.extensions.encrypt import decode
from tmaps.api import api

from tmaps.tools import get_tool



@api.route('/tools/<tool_id>/request', methods=['POST'])
@jwt_required()
def process_tool_request(tool_id):
    """
    Process a generic tool request sent by the client.
    POST payload should have the format:

    {
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
    payload = data.get('payload', {})

    # Create the tool object
    # TODO: Could theoretically initialize the new tool instance with data that
    # was saved previously in the DB using a special id that the client knows
    # and can send with subsequent tool requests.
    # This concept was previously implemented in the form of "ToolInstances".
    # It could be reintroduced if necessary. Due to changes on the client side,
    # a better name would be "ToolSession" or something. The tool creator
    # could save data on the tool object, which would then be saved on the db
    # and automatically restored on the next request. The tool creator wouldn't
    # know that the tool instance is destroyed after each request.
    tool_cls = get_tool(tool_id)
    tool = tool_cls()

    tool_res = tool.process_request(payload)

    return jsonify(result=tool_res)


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
