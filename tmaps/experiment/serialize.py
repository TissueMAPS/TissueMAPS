from tmaps.experiment import Experiment, Channel, ChannelLayer
from tmaps.serialize import json_encoder
from tmaps.model import encode_pk


@json_encoder(Experiment)
def encode_experiment(obj, encoder):
    mapobject_info = []
    for t in obj.mapobject_types:
        mapobject_info.append({
            'mapobject_type_name': t.name,
            'features': [{'name': f.name} for f in t.features]
        })
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
        'mapobject_info': mapobject_info,
        'plates': [pl.as_dict() for pl in obj.plates]
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
    image_height, image_width = obj.image_size
    return {
        'id': encode_pk(obj.id),
        'zplane': obj.zplane,
        'tpoint': obj.tpoint,
        'image_size': {
            'width': image_width,
            'height': image_height
        }
    }
