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
from tmserver.serialize import json_encoder
from tmserver.model import encode_pk

from tmlib.tools.result import ToolResult, LabelLayer, Plot


@json_encoder(ToolResult)
def encode_tool_result(obj, encoder):
    return {
        'id': encode_pk(obj.id),
        'name': obj.name,
        'submission_id': obj.submission_id,
        'layer': obj.layer,
        'plots': map(encoder.default, obj.plots)
    }


@json_encoder(LabelLayer)
def encode_label_layer(obj, encoder):
    return {
        'id': encode_pk(obj.id),
        'type': obj.type,
        'attributes': obj.attributes
    }


@json_encoder(Plot)
def encode_plot(obj, encoder):
    return {
        'id': encode_pk(obj.id),
        'type': obj.type,
        'attributes': obj.attributes
    }


