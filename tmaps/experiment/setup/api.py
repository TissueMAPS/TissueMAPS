# import json

# from tmaps.api import api
# from flask.ext.jwt import jwt_required
# from flask.ext.jwt import current_identity
# from flask import jsonify, request
# from werkzeug import secure_filename

# from tmaps.extensions.gc3pie import gc3pie_engine
# from tmaps.experiment import Experiment
# from tmaps.experiment.setup import Plate, PlateSource, PlateAcquisition
# # from tmaps.experiment.setup import Task
# from tmaps.extensions import db
# from tmaps.response import *


# # @api.route('/tasks/<int:task_id>', methods=['GET'])
# # @jwt_required()
# # def get_task_info(task_id):
# #     task = Task.get(task_id)
# #     return jsonify(gc3pie_engine.get_task_data(task))


# @api.route('/experiments/<experiment_id>/plate-sources', methods=['GET'])
# @jwt_required()
# def get_plate_sources(experiment_id):
#     e = Experiment.get(experiment_id)
#     if not e.belongs_to(current_identity):
#         return NOT_AUTHORIZED_RESPONSE

#     return jsonify(plate_sources=[pl.as_dict() for pl in e.plate_sources])


# @api.route('/experiments/<experiment_id>/plate-sources',
#                  methods=['POST'])
# @jwt_required()
# def create_plate_source(experiment_id):
#     """
#     Create a new plate source directory for the experiment with id `experiment_id`.

#     Request
#     -------

#     {
#         name: string,
#         description: string
#     }

#     Response
#     --------

#     PlateSource object

#     """
#     data = json.loads(request.data)
#     pls_name = data.get('name')
#     pls_desc = data.get('description', '')

#     if not pls_name:
#         return MALFORMED_REQUEST_RESPONSE

#     e = Experiment.get(experiment_id)
#     if not e:
#         return RESOURCE_NOT_FOUND_RESPONSE

#     if not e.belongs_to(current_identity):
#         return NOT_AUTHORIZED_RESPONSE

#     pls = PlateSource.create(
#         name=pls_name, description=pls_desc, experiment=e)

#     return jsonify(pls.as_dict())


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
