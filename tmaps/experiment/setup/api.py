import json

from flask.ext.jwt import jwt_required
from flask.ext.jwt import current_identity
from flask import jsonify, request

from tmlib.models import Experiment, Plate

from tmaps.serialize import json_encoder
from tmaps.model import encode_pk
from tmaps.extensions import db
from tmaps.api import api
from tmaps.response import (
    MALFORMED_REQUEST_RESPONSE,
    NOT_AUTHORIZED_RESPONSE,
    RESOURCE_NOT_FOUND_RESPONSE
)



# @api.route('/plate-sources/<int:pls_id>/acquisitions', methods=['POST'])
# @jwt_required()
# def create_acquisition(pls_id):
#     """
#     Create a new acquisition directory for the plate source with it `pls_id`.

#     Request
#     -------

#     {
#         name: string,
#         description: string
#     }

#     Response
#     --------

#     acquisition object as returned by PlateAcquisition.as_dict

#     """
#     data = json.loads(request.data)
#     aq_name = data.get('name')
#     aq_desc = data.get('description', '')

#     if not aq_name:
#         return MALFORMED_REQUEST_RESPONSE

#     pl = PlateSource.query.get(pls_id)
#     if not pl:
#         return RESOURCE_NOT_FOUND_RESPONSE

#     if not pl.experiment.belongs_to(current_identity):
#         return NOT_AUTHORIZED_RESPONSE

#     aq = PlateAcquisition.create(
#         name=aq_name, description=aq_desc, plate_source=pl)

#     return jsonify(aq.as_dict())


# @api.route('/plate-sources/<int:pls_id>', methods=['DELETE'])
# @jwt_required()
# def delete_plate_source(pls_id):
#     pl = PlateSource.query.get(pls_id)
#     if not pl:
#         return RESOURCE_NOT_FOUND_RESPONSE
#     if not pl.experiment.belongs_to(current_identity):
#         return NOT_AUTHORIZED_RESPONSE
#     pl.delete()
#     return 'PlateSource successfully removed', 200


# @api.route('/acquisitions/<int:aq_id>', methods=['DELETE'])
# @jwt_required()
# def delete_acquisition(aq_id):
#     aq = PlateAcquisition.query.get(aq_id)
#     if not aq:
#         return 'No acquisition found', 404
#     if not aq.plate_source.experiment.belongs_to(current_identity):
#         return 'User has no permission to access this acquisition', 401
#     db.session.delete(aq)
#     db.session.commit()
#     return 'PlateAcquisition successfully removed', 200
