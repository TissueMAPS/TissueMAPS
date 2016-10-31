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
        'error': True,
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
