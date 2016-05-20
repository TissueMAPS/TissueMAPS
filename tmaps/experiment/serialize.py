from tmlib.models import (
    Experiment, Channel, ChannelLayer, Plate, Acquisition,
    Feature, MapobjectType
)
from tmaps.serialize import json_encoder
from tmaps.model import encode_pk
from tmlib.workflow.canonical import CanonicalWorkflowDescription


@json_encoder(Experiment)
def encode_experiment(obj, encoder):
    return {
        'id': encode_pk(obj.id),
        'name': obj.name,
        'description': obj.description,
        'user': obj.user.name,
        'plate_format': obj.plate_format,
        'microscope_type': obj.microscope_type,
        'plate_acquisition_mode': obj.plate_acquisition_mode,
        'status': obj.status,
        'channels': map(encoder.default, obj.channels),
        'mapobject_types': map(encoder.default, obj.mapobject_types),
        'plates': [p.id for p in obj.plates],
        # TODO: Load the previous one if it exists
        'workflow_description': CanonicalWorkflowDescription().as_dict()
    }


@json_encoder(Channel)
def encode_channel(obj, encoder):
    return {
        'id': encode_pk(obj.id),
        'name': obj.name,
        'layers': [encoder.default(ch) for ch in obj.layers]
    }


@json_encoder(ChannelLayer)
def encode_channel_layer(obj, encoder):
    # Get the image size on the highest zoom level (last element in the list)
    image_height, image_width = obj.image_size[-1]
    return {
        'id': encode_pk(obj.id),
        'zplane': obj.zplane,
        'tpoint': obj.tpoint,
        'max_zoom': obj.maxzoom_level_index,
        'image_size': {
            'width': image_width,
            'height': image_height
        }
    }


@json_encoder(Plate)
def encode_plate(obj, encoder):
    return {
        'id': encode_pk(obj.id),
        'name': obj.name,
        'description': obj.description,
        'experiment_id': encode_pk(obj.experiment_id),
        'acquisitions': map(encoder.default, obj.acquisitions)
    }


@json_encoder(Acquisition)
def encode_acquisition(obj, encoder):
    return {
        'id': encode_pk(obj.id),
        'name': obj.name,
        'description': obj.description,
        'plate_id': encode_pk(obj.plate_id),
        'status': obj.status
    }


@json_encoder(Feature)
def encode_feature(obj, encoder):
    return {
        'id': encode_pk(obj.id),
        'name': obj.name
    }


@json_encoder(MapobjectType)
def encode_mapobject_type(obj, encoder):
    return {
        'id': encode_pk(obj.id),
        'name': obj.name,
        'features': map(encoder.default, obj.features)
    }
