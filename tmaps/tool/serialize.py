from tmaps.tool import Tool
from tmaps.serialize import json_encoder


@json_encoder(Tool)
def encode_tool(obj, encoder):
    return {
        'id': obj.hash,
        'name': obj.name,
        'description': obj.description,
        'icon': obj.icon
    }
