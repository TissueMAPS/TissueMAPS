import sqlalchemy

from base import *
from utils import *
from tmlib.models import Model


def _get_with_hash(self, h):
    try:
        pk = decode_pk(h)
    except ValueError:
        return None
    else:
        return self.get(pk)
setattr(sqlalchemy.orm.Query, 'get_with_hash', _get_with_hash)


@property
def _monkeypatched_hash_property(self):
    return encode_pk(self.id)
setattr(Model, 'hash', _monkeypatched_hash_property)
