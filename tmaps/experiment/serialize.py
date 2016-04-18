from tmlib.models import Experiment, Channel, ChannelLayer, Plate, Acquisition
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
        'plates': obj.plates
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
        'acquisitions': obj.acquisitions
    }


@json_encoder(Acquisition)
def encode_acquisition(obj, encoder):
    return {
        'id': encode_pk(obj.id),
        'name': obj.name,
        'description': obj.description,
        'plate_id': encode_pk(obj.plate_id),
        'status': obj.status,
        'microscope_image_files':
            [{'name': f.name} for f in obj.microscope_image_files],
        'microscope_metadata_files':
            [{'name': f.name} for f in obj.microscope_image_files]
    }
