import json

from models import LayerMod
from db import db


class Tool(object):

    def __init__(self, socket, _dbobject):

        self.experiment_dataset = _dbobject.experiment.dataset
        self.client_proxy = ClientProxy(socket, _dbobject)
        self._dbobject = _dbobject

    @property
    def data_storage(self):
        return self._dbobject.data_storage

    @data_storage.setter
    def data_storage(self, val):
        self._dbobject.data_storage = val
        db.session.commit()


class ClientProxy(object):

    def __init__(self, socket, tool_instance):
        self.socket = socket
        self.tool_instance = tool_instance

        if not socket:
            print 'WARNING: socket is None; can\'t communicate with client'

    def log(self, msg):
        if not self.socket:
            return

        data = {
            'event': 'log',
            'data': msg
        }
        self.socket.send(json.dumps(data))

    def add_layer_mod(self, name, source, funcname, render_args={},
                      modfunc_arg=None):

        if not self.socket:
            return

        render_args_ = {}
        if source == 'outline':
            default_render_args = {
                'black_as_alpha': True
            }
            render_args_.update(default_render_args)
            render_args_.update(render_args)
        if source == 'area':
            default_render_args = {
                'black_as_alpha': True
            }
            render_args_.update(default_render_args)
            render_args_.update(render_args)

        layermod = LayerMod(
            name=name,
            source=source,
            tool_method_name=funcname,
            tool_id=self.tool_instance.tool_id,
            appstate_id=self.tool_instance.appstate_id,
            experiment_id=self.tool_instance.experiment_id,
            render_args=render_args_,
            modfunc_arg=modfunc_arg
        )

        db.session.add(layermod)
        db.session.commit()

        self.socket.send(json.dumps({
            'event': 'add_layermod',
            'data': {
                'layermod': layermod.as_dict()
            }
        }))
