"""
Serialization mechanism for TissueMAPS. Please refer to
:py:class:`TmJSONEncoder` for further information.

"""
import flask

_serializers = {}


def json_encoder(obj_type):
    def wrap(f):
        _serializers[obj_type] = f
        return f
    return wrap


class TmJSONEncoder(flask.json.JSONEncoder):
    """
    Custom JSON encoder to serialize types defined for TissueMAPS.
    This serializer will also check supertypes if no matching serializer was
    found.
    Serializers need to be registered with the ``json_encoder`` decorator:

    @json_encoder(SomeClass)
    def encode_some_class(obj, encoder):
        return {
            'id': encode_pk(obj.id)
            ...
        }

    Make sure that the files where the serializers are defined are imported at
    application start, otherwise they won't be registered.

    """
    def _serialize_as_type(self, obj, t):
        if t is None:
            return None
        elif t in _serializers:
            return _serializers[t](obj, self)
        else:
            return self._serialize_as_type(obj, t.__base__)

    def default(self, obj):
        """Overridden serializer function invoked by flask"""
        serialized = self._serialize_as_type(obj, type(obj))
        if serialized is not None:
            return serialized
        else:
            return flask.json.JSONEncoder.default(self, obj)
