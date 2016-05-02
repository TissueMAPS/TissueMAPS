from sqlalchemy import Column, String, Text

from tmaps.serialize import json_encoder
from tmaps.model import Model


class Tool(Model):
    __tablename__ = 'tools'

    name = Column(String(120))
    icon = Column(String(120))
    description = Column(Text)
    full_class_path = Column(String(120))

    def get_class(self):
        def import_from_str(name):
            components = name.split('.')
            mod = __import__(components[0])
            for comp in components[1:]:
                mod = getattr(mod, comp)
            return mod
        cls = import_from_str(self.full_class_path)
        return cls

    def to_dict(self):
        return {
            'id': self.hash,
            'name': self.name,
            'description': self.description,
            'icon': self.icon
        }


@json_encoder(Tool)
def encode_tool(obj, encoder):
    return {
        'id': obj.hash,
        'name': obj.name,
        'description': obj.description,
        'icon': obj.icon
    }
