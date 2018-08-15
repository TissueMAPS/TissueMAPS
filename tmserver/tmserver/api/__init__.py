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
RESTful API.

"""

from flask import Blueprint

api = Blueprint('api', __name__)

# load all API entry points to register with Blueprint
import tmserver.api.experiment
import tmserver.api.plate
import tmserver.api.acquisition
import tmserver.api.channel
import tmserver.api.cycle
import tmserver.api.well
import tmserver.api.site
import tmserver.api.file
import tmserver.api.user
import tmserver.api.mapobject
import tmserver.api.feature
import tmserver.api.layer
import tmserver.api.tile

import tmserver.api.tools

import tmserver.api.workflow
