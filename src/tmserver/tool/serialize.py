from tmserver.serialize import json_encoder
from tmserver.util import encode_pk

from tmtoolbox.result import ToolResult, LabelLayer, Plot


@json_encoder(ToolResult)
def encode_tool_result(obj, encoder):
    return {
        'id': encode_pk(obj.id),
        'name': obj.name,
        'layer': obj.layer,
        'plots': map(encoder.default, obj.plots)
    }


@json_encoder(LabelLayer)
def encode_label_layer(obj, encoder):
    return {
        'id': encode_pk(obj.id),
        'name': 'TODO:NAME',
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


