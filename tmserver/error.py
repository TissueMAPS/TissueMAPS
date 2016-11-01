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
"""
Custom exception types and associated serializers.
When raised these exceptions will be automatically handled and serialized by
the flask error handler and sent to the client.

"""
import sqlalchemy
from flask import jsonify, current_app

from tmserver.serialize import json_encoder
from api import api


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
def handle_no_result_found(error):
    response = jsonify(error={
        'message': error.message,
        'status_code': 404,
        'type': error.__class__.__name__
    })
    current_app.logger.error('NoResultFound: ' + error.message)
    response.status_code = 404
    return response


@api.errorhandler(sqlalchemy.exc.IntegrityError)
def handle_integrity_error(error):
    response = jsonify(error={
        'error': True,
        'message': error.message,
        'status_code': 500,
        'type': error.__class__.__name__
    })
    current_app.logger.error('IntegrityError: ' + error.message)
    response.status_code = 500
    return response


@register_error
class APIException(Exception):
    def __init__(self, message, status_code):
        self.message = message
        self.status_code = status_code

    def __str__(self):
        return '%s: %s' % (self.__class__.__name__, self.message)


@json_encoder(APIException)
def encode_api_exception(obj, encoder):
    return {
        'error': True,
        'message': obj.message,
        'status_code': obj.status_code,
        'type': obj.__class__.__name__
    }


@register_error
class MalformedRequestError(APIException):

    default_message = 'Invalid request'

    def __init__(self, message=default_message):
        super(MalformedRequestError, self).__init__(
            message=message, status_code=400
        )


@register_error
class MissingGETParameterError(MalformedRequestError):
    def __init__(self, *parameters):
        super(MissingGETParameterError, self).__init__(
            message=(
                'The following GET parameters are required but were missing'
                ' in the request: "%s".' % '", "'.join(parameters)
            )
        )


@register_error
class MissingPOSTParameterError(MalformedRequestError):
    def __init__(self, *parameters):
        super(MissingPOSTParameterError, self).__init__(
            message=(
                'The following POST parameters are required but were missing'
                ' in the request body: "%s".' % '", "'.join(parameters)
            )
        )


@register_error
class NotAuthorizedError(APIException):

    default_message = 'This user does not have access to this resource.'

    def __init__(self, message=default_message):
        super(NotAuthorizedError, self).__init__(
            message=message, status_code=401
        )


@register_error
class ResourceNotFoundError(APIException):
    def __init__(self, model):
        super(ResourceNotFoundError, self).__init__(
            message=(
                'The requested resource with type "%s" was not found.' % model.__name__
            ),
            status_code=404
        )


@register_error
class InternalServerError(APIException):

    default_message = 'The server encountered an unexpected problem.'

    def __init__(self, message=default_message):
        super(InternalServerError, self).__init__(
            message=message, status_code=500
        )
