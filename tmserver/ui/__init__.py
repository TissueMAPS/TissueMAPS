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
import logging
from flask import Blueprint, current_app, jsonify

from tmserver.error import register_http_error_classes

ui = Blueprint('ui', __name__)

logger = logging.getLogger(__name__)


def register_error(cls):
    """Decorator to register exception classes as errors that can be
    serialized to JSON"""
    @ui.errorhandler(cls)
    def handle_invalid_usage(error):
        current_app.logger.error(error)
        response = jsonify(error=error)
        response.status_code = error.status_code
        return response
    return cls


register_http_error_classes(register_error)


import tmserver.ui.tools
import tmserver.ui.layer
