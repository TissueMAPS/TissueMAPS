from sqlalchemy import Column, String, Text
from abc import ABCMeta
from abc import abstractmethod

from tmaps.serialize import json_encoder
from tmaps.model import Model


class Tool(Model):
    __tablename__ = 'tools'

    name = Column(String(120), index=True)
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


class ToolRequestHandler(object):

    __metaclass__ = ABCMeta

    @abstractmethod
    def process_request(self, payload, tool_session, experiment, use_spark=False):
        """
        Process a tool request sent by the client.

        Parameters
        ----------
        payload : dict
            An arbitrary dictionary sent by the client tool.
        tool_session : tmaps.tool.ToolSession
            A session of a specific tool. This object enables information
            to persists over multiple requests (e.g. for iterative classifier
            training).
        experiment : tmlib.models.Experiment
            The experiment from which the request was sent.
        use_spark : boolean
            If the tool should try to use Apache Spark for processing.

        """
        pass
