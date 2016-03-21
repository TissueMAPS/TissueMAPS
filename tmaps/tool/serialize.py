from tmaps.tool import Tool
from tmaps.serialize import json_encoder
from tmaps.model import encode_pk


@json_encoder(Tool)
def encode_tool(obj, encoder):
    return {
        'id': encode_pk(obj.hash),
        'name': obj.name,
        'description': obj.description,
        'icon': obj.icon
    }
