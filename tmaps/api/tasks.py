from flask import jsonify
from flask.ext.jwt import jwt_required
from flask.ext.jwt import current_identity

from tmaps.models import Task
from tmaps.extensions.gc3pie import gc3pie_engine

from . import api

@api.route('/tasks/<int:task_id>', methods=['GET'])
@jwt_required()
def get_task_info(task_id):
    task = Task.get(task_id)
    return jsonify(gc3pie_engine.get_task_data(task))
