import flask

_serializers = {}


def json_encoder(obj_type):
    def wrap(f):
        _serializers[obj_type] = f
        return f
    return wrap


class TmJSONEncoder(flask.json.JSONEncoder):
    def default(self, obj):
        if type(obj) in _serializers:
            return _serializers[type(obj)](obj, self)
        else:
            for cls in type(obj).__bases__:
                if cls in _serializers:
                    return _serializers[cls](obj, self)
        return flask.json.JSONEncoder.default(self, obj)
