# TmServer - TissueMAPS server application.
# Copyright (C) 2016-2018 University of Zurich.
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
"""Serialization mechanism for TissueMAPS database model objects."""
import flask

import tmlib.models as tm

from tmserver.model import encode_pk

_serializers = {}


def json_encoder(obj_type):
    """Decorator for functions that JSON serialiaze objects."""
    def wrap(f):
        _serializers[obj_type] = f
        return f
    return wrap


class TmJSONEncoder(flask.json.JSONEncoder):

    """Custom JSON encoder to serialize types defined for TissueMAPS.
    This serializer will also check supertypes if no matching serializer was
    found.
    Serializers need to be registered with the ``json_encoder`` decorator::

        @json_encoder(SomeClass)
        def encode_some_class(obj, encoder):
            return {
                'id': encode_pk(obj.id)
                ...
            }

    Make sure that the files where the serializers are defined are imported at
    application start, otherwise they won't be registered.

    """
    def _serialize_as_type(self, obj, t):
        if t is None:
            return None
        elif t in _serializers:
            return _serializers[t](obj, self)
        else:
            return self._serialize_as_type(obj, t.__base__)

    def default(self, obj):
        """Overridden serializer function invoked by flask"""
        serialized = self._serialize_as_type(obj, type(obj))
        if serialized is not None:
            return serialized
        else:
            return flask.json.JSONEncoder.default(self, obj)


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
        'image_size': {
            'width': obj.channel.experiment.pyramid_width,
            'height': obj.channel.experiment.pyramid_height
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
        'plate_name': obj.plate.name
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
        'index': obj.index,
        'tpoint': obj.tpoint
    }


@json_encoder(tm.Well)
def encode_well(obj, encoder):
    return {
        'id': encode_pk(obj.id),
        'name': obj.name,
        'description': obj.description,
        'plate_name': obj.plate.name,
        'dimensions': list(obj.dimensions)
    }


@json_encoder(tm.Site)
def encode_site(obj, encoder):
    return {
        'id': encode_pk(obj.id),
        'y': obj.y,
        'x': obj.x,
        'height': obj.height,
        'width': obj.width,
        'well_name': obj.well.name,
        'plate_name': obj.well.plate.name
        # TODO: shifts ?
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
        'layers': [encoder.default(layer) for layer in obj.layers]
    }


@json_encoder(tm.SegmentationLayer)
def encode_segmentation_layer(obj, encoder):
    return {
        'id': encode_pk(obj.id),
        'tpoint': obj.tpoint,
        'zplane': obj.zplane,
        'image_size': {
            'width': obj.mapobject_type.experiment.pyramid_width,
            'height': obj.mapobject_type.experiment.pyramid_height
        }
    }


@json_encoder(tm.MicroscopeImageFile)
def encode_microscope_image_file(obj, encoder):
    return {
        'id': encode_pk(obj.id),
        'name': obj.name,
        'status': obj.status
    }


@json_encoder(tm.MicroscopeMetadataFile)
def encode_microscope_metadata_file(obj, encoder):
    return {
        'id': encode_pk(obj.id),
        'name': obj.name,
        'status': obj.status
    }


@json_encoder(tm.ToolResult)
def encode_tool_result(obj, encoder):
    return {
        'id': encode_pk(obj.id),
        'name': obj.name,
        'submission_id': obj.submission_id,
        'tool_name': obj.tool_name,
        'type': obj.type,
        'attributes': obj.attributes,
        'layers': [encoder.default(layer) for layer in obj.mapobject_type.layers],
        'plots': map(encoder.default, obj.plots)
    }


@json_encoder(tm.Plot)
def encode_plot(obj, encoder):
    return {
        'id': encode_pk(obj.id),
        'type': obj.type,
        'attributes': obj.attributes
    }
