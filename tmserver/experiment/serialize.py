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
"""Serialization for experiment-related types"""

import tmlib.models as tm
from tmserver.serialize import json_encoder
from tmserver.model import encode_pk
from tmlib.workflow.description import WorkflowDescription


@json_encoder(tm.ExperimentReference)
def encode_experiment(obj, encoder):
    return {
        'id': encode_pk(obj.id),
        'name': obj.name,
        'description': obj.description,
        'user': obj.user.name
    }


@json_encoder(tm.Channel)
def encode_channel(obj, encoder):
    return {
        'id': encode_pk(obj.id),
        'name': obj.name,
        'bit_depth': obj.bit_depth,
        'layers': [encoder.default(ch) for ch in obj.layers],
    }


@json_encoder(tm.ChannelLayer)
def encode_channel_layer(obj, encoder):
    return {
        'id': encode_pk(obj.id),
        'max_zoom': obj.maxzoom_level_index,
        'tpoint': obj.tpoint,
        'zplane': obj.zplane,
        'max_intensity': obj.max_intensity,
        'min_intensity': obj.min_intensity,
        'experiment_id': encode_pk(obj.channel.experiment_id),
        'image_size': {
            'width': obj.width,
            'height': obj.height
        }
    }


@json_encoder(tm.Plate)
def encode_plate(obj, encoder):
    return {
        'id': encode_pk(obj.id),
        'name': obj.name,
        'description': obj.description,
        'acquisitions': map(encoder.default, obj.acquisitions),
        'status': obj.status,
    }


@json_encoder(tm.Acquisition)
def encode_acquisition(obj, encoder):
    return {
        'id': encode_pk(obj.id),
        'name': obj.name,
        'description': obj.description,
        'status': obj.status,
    }


@json_encoder(tm.MicroscopeImageFile)
def enocode_microscope_image_file(obj, encoder):
    return {
        'name': obj.name,
        'status': obj.status
    }


@json_encoder(tm.MicroscopeMetadataFile)
def enocode_microscope_metadata_file(obj, encoder):
    return {
        'name': obj.name,
        'status': obj.status
    }


@json_encoder(tm.Cycle)
def encode_cycle(obj, encoder):
    return {
        'id': encode_pk(obj.id),
        'plate_id': encode_pk(obj.plate_id),
    }


@json_encoder(tm.Feature)
def encode_feature(obj, encoder):
    return {
        'id': encode_pk(obj.id),
        'name': obj.name,
    }


@json_encoder(tm.MapobjectType)
def encode_mapobject_type(obj, encoder):
    return {
        'id': encode_pk(obj.id),
        'name': obj.name,
        'features': map(encoder.default, obj.features),
    }


@json_encoder(tm.MicroscopeImageFile)
def encode_microscope_image_file(obj, encoder):
    return {
        'name': obj.name,
        'status': obj.status
    }


@json_encoder(tm.MicroscopeMetadataFile)
def encode_microscope_metadata_file(obj, encoder):
    return {
        'name': obj.name,
        'status': obj.status
    }
