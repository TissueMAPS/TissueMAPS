import tmlib.models as tm
from tmserver.serialize import json_encoder
from tmserver.model import encode_pk
from tmlib.workflow.description import WorkflowDescription


@json_encoder(tm.Experiment)
def encode_experiment(obj, encoder):
    return {
        'id': encode_pk(obj.id),
        'name': obj.name,
        'description': obj.description,
        'user': obj.user.name,
        'plate_format': obj.plate_format,
        'microscope_type': obj.microscope_type,
        'plate_acquisition_mode': obj.plate_acquisition_mode,
        # 'channels': map(encoder.default, obj.channels),
        'mapobject_types': map(encoder.default, obj.mapobject_types),
        'workflow_description': obj.workflow_description.as_dict()
    }


@json_encoder(tm.Channel)
def encode_channel(obj, encoder):
    return {
        'id': encode_pk(obj.id),
        'name': obj.name,
        'bit_depth': obj.bit_depth,
        'layers': [encoder.default(ch) for ch in obj.layers],
        'experiment_id': encode_pk(obj.experiment_id)
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
        'experiment_id': encode_pk(obj.experiment_id),
        'acquisitions': map(encoder.default, obj.acquisitions),
        'status': obj.status,
        'experiment_id': encode_pk(obj.experiment_id)
    }


@json_encoder(tm.Acquisition)
def encode_acquisition(obj, encoder):
    return {
        'id': encode_pk(obj.id),
        'name': obj.name,
        'description': obj.description,
        'plate_id': encode_pk(obj.plate_id),
        'status': obj.status,
        'experiment_id': encode_pk(obj.plate.experiment_id)
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
        'experiment_id': encode_pk(obj.mapobject_type.experiment_id)
    }


@json_encoder(tm.MapobjectType)
def encode_mapobject_type(obj, encoder):
    return {
        'id': encode_pk(obj.id),
        'name': obj.name,
        'features': map(encoder.default, obj.features),
        'experiment_id': encode_pk(obj.experiment_id)
    }


@json_encoder(tm.MicroscopeImageFile)
def encode_microscope_image_file(obj, encoder):
    return {
        'name': obj.name,
        'upload_status': obj.upload_status


@json_encoder(tm.MicroscopeMetadataFile)
def encode_microscope_metadata_file(obj, encoder):
    return {
        'name': obj.name,
        'upload_status': obj.upload_status
    }
    }
