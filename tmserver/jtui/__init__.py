import logging
from flask import Blueprint, current_app, jsonify

from tmserver.error import register_http_error_classes

jtui = Blueprint('jtui', __name__)

logger = logging.getLogger(__name__)


def register_error(cls):
    """Decorator to register exception classes as errors that can be
    serialized to JSON"""
    @jtui.errorhandler(cls)
    def handle_invalid_usage(error):
        current_app.logger.error(error)
        response = jsonify(error=error)
        response.status_code = error.status_code
        return response
    return cls

register_http_error_classes(register_error)

import tmserver.jtui.api


