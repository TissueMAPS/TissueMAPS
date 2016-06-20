import json

from flask import jsonify, request
from flask.ext.jwt import jwt_required
from flask.ext.jwt import current_identity

from tmaps.appstate import Appstate
from tmaps.user import User
from tmaps.extensions import db
from tmaps.api import api
from tmaps.model import decode_pk


# @api.route('/appstates/<appstate_id>', methods=['GET'])
# @jwt_required()
# def get_appstate(appstate_id):
#     """
#     Get all an state for the current user.

#     Response:

#     {
#         "id": int,
#         "name": string,
#         "blueprint": string
#     }

#     """
#     appstate_id = decode(appstate_id)
#     state = AppState.query.get(appstate_id)

#     if not state:
#         return 'No appstate found', 404
#     if not state.is_editable_by_user(current_identity):
#         return 'You do not have permission to access this state', 401

#     return jsonify(state.as_dict())

# @api.route('/appstates', methods=['GET'])
# @jwt_required()
# def get_appstates():
#     """
#     Get all app states for the current user.
#     These states may either belong to the current user or were shared with him.

#     Return value:

#     {
#         "owned": {
#             {
#                 "id": int,
#                 "name": string,
#                 "blueprint": string
#             },
#             ...
#         },
#         "shared": [
#             {
#                 "id": int,
#                 "name": string,
#                 "blueprint": string
#             },
#             ...
#         ]
#     }

#     """

#     states_owned = [st.as_dict() for st in current_identity.appstates]
#     shares = AppStateShare.query.\
#         filter_by(recipient_user_id=current_identity.id).\
#         all()
#     states_received = [sh.appstate.as_dict() for sh in shares]

#     return jsonify({
#         'owned': states_owned,
#         'shared': states_received
#     })


# @api.route('/snapshots/<appstate_id>', methods=['GET'])
# def appstate(appstate_id):
#     appstate_id = decode(appstate_id)

#     st = AppStateSnapshot.query.get(appstate_id)
#     if not st:
#         return 'No snapshot s found', 404
#     elif not st.is_snapshot:
#         return 'appstate isn\'t shared publicly', 401
#     else:
#         return jsonify(st.as_dict())


# @api.route('/appstates/<appstate_id>', methods=['PUT'])
# @jwt_required()
# def update_appstate(appstate_id):
#     """
#     Update the app state with id `appstate_id` for the current user.
#     Payload should have the format:

#     {
#         blueprint: string
#     }

#     """
#     appstate_id = decode(appstate_id)
#     data = json.loads(request.data)
#     bp = data.get('blueprint')

#     if not bp:
#         return 'No blueprint in request', 400

#     st = AppState.query.get(appstate_id)

#     if not st:
#         return 'No appstate found', 404
#     else:
#         st.blueprint = bp
#         db.session.commit()
#         return jsonify(st.as_dict())


# @api.route('/appstates/<appstate_id>', methods=['DELETE'])
# @jwt_required()
# def delete_appstate(appstate_id):
#     """Delete the AppState with id `appstate_id`."""
#     appstate_id = decode(appstate_id)
#     st = AppState.query.get(appstate_id)
#     if not st:
#         return 'No appstate found', 404
#     if st.is_editable_by_user(current_identity):
#         db.session.delete(st)
#         db.session.commit()
#     else:
#         return 'You have no permission to edit this appstate', 401


# @api.route('/appstates', methods=['POST'])
# @jwt_required()
# def save_appstate():
#     """
#     Save an app state for the current user.
#     POST payload should have the format:

#     {
#         name: name,
#         description: description,
#         blueprint: object
#     }

#     Response:

#     {
#         object
#     }

#     where object is the serialized AppState containing an id property.

#     """

#     data = json.loads(request.data)
#     name = data.get('name')
#     bp = data.get('blueprint')
#     description = data.get('description')

#     if not name or not bp:
#         return 'No "name" or no "blueprint" in request', 400

#     app = AppState(
#         name=name, blueprint=bp, owner_id=current_identity.id,
#         description=description
#     )
#     db.session.add(app)
#     db.session.commit()

#     return jsonify(app.as_dict())


# @api.route('/appstates/<appstate_id>/snapshots', methods=['POST'])
# @jwt_required()
# def share_appstate_by_link(appstate_id):
#     """
#     Activate link-sharing for this appstate.
#     AppStates that are shared by link are accessible by anyone that has the
#     link with read-only rights.

#     """
#     appstate_id = decode(appstate_id)
#     appstate = AppState.query.get(appstate_id)
#     if not appstate:
#         return 'No appstate found', 404
#     if appstate.is_editable_by_user(current_identity):
#         snapshot = appstate.create_snapshot()
#         return jsonify(snapshot.as_dict()), 200
#     else:
#         return 'You have no permission to share this appstate', 401


# @api.route('/appstates/<appstate_id>/share_by_link', methods=['DELETE'])
# @jwt_required()
# def deactivate_share_appstate_by_link(appstate_id):
#     """Deactivate link-sharing for this appstate."""
#     appstate_id = decode(appstate_id)
#     appstate = AppState.query.get(appstate_id)
#     if not appstate:
#         return 'No appstate found', 404
#     if appstate.is_editable_by_user(current_identity):
#         appstate.shared_by_link = False
#         appstate.uuid = None
#         db.session.commit()
#         return 'AppState was unshared successfully', 200
#     else:
#         return 'You have no permission to share this appstate', 401


# @api.route('/appstates/<appstate_id>/share_with_users', methods=['PUT'])
# @jwt_required()
# def share_appstate_with_users(appstate_id):
#     """
#     Share an app state of the current user with multiple other users
#     and optionally send an email to those users.

#     The POST payload should have the format:

#     {
#         # the users with which to share the app state (username or email).
#         users: [
#             {
#                 name: username_XY,
#                 edit: boolean
#                 ...
#             }
#         ],
#         email: {
#             subject: string,
#             body: string
#         }
#     }

#     """
#     appstate_id = decode(appstate_id)
#     appstate = AppState.query.get(appstate_id)
#     if not appstate:
#         return 'No appstate found', 404
#     if not appstate.is_editable_by_user(current_identity):
#         return 'You have no permission to share this appstate', 401

#     data = json.loads(request.data)
#     usernames = [u.name for u in data.get('users', [])]
#     if not usernames:
#         return 'No users in request payload', 400

#     users = User.query.filter(User.name.in_(usernames))
#     if not users:
#         return 'No users under these ids found', 404

#     for user in users:
#         share = AppStateShare(
#             recipient_user_id=user.id,
#             donor_user_id=current_identity.id,
#             appstate_id=appstate.id)
#         db.session.add(share)

#     db.session.commit()

#     email = data.get('email')
#     if email:
#         pass
#         # email_adresses = [u.email for u in users]
#         # TODO: send email with email['subject'] and email['body']
#         # to email_adresses

#     return 'Sharing operation successful', 200
