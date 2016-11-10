# TmServer - TissueMAPS server application.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""RESTful API.

"""
import logging
import sqlalchemy
from flask import Blueprint, current_app, jsonify

from tmserver.error import register_http_error_classes

api = Blueprint('api', __name__)

logger = logging.getLogger(__name__)


def register_error(cls):
    """Decorator to register exception classes as errors that can be
    serialized to JSON"""
    @api.errorhandler(cls)
    def handle_invalid_usage(error):
        current_app.logger.error(error)
        response = jsonify(error=error)
        response.status_code = error.status_code
        return response
    return cls


@api.errorhandler(sqlalchemy.orm.exc.NoResultFound)
def _handle_no_result_found(error):
    response = jsonify(error={
        'message': error.message,
        'status_code': 404,
        'type': error.__class__.__name__
    })
    current_app.logger.error('NoResultFound: ' + error.message)
    response.status_code = 404
    return response


@api.errorhandler(sqlalchemy.exc.IntegrityError)
def _handle_integrity_error(error):
    response = jsonify(error={
        'error': True,
        'message': error.message,
        'status_code': 500,
        'type': error.__class__.__name__
    })
    current_app.logger.error('IntegrityError: ' + error.message)
    response.status_code = 500
    return response


register_http_error_classes(register_error)


import tmserver.api.experiment
import tmserver.api.workflow
import tmserver.api.upload
import tmserver.api.user
import tmserver.api.mapobject
import tmserver.api.layer
import tmserver.api.tools
