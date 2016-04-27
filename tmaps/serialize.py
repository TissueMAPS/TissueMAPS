import flask

_serializers = {}


def json_encoder(obj_type):
    def wrap(f):
        _serializers[obj_type] = f
        return f
    return wrap


class TmJSONEncoder(flask.json.JSONEncoder):
    def _serialize_as_type(self, obj, t):
        if t is None:
            return None
        elif t in _serializers:
            return _serializers[t](obj, self)
        else:
            return self._serialize_as_type(obj, t.__base__)

    def default(self, obj):
        serialized = self._serialize_as_type(obj, type(obj))
        if serialized is not None:
            return serialized
        else:
            return flask.json.JSONEncoder.default(self, obj)
