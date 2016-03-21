from tmlib.models.utils import decode_pk as _decode_pk
import sqlalchemy

def _get_with_hash(self, h):
    return self.get(_decode_pk(h))
setattr(sqlalchemy.orm.Query, 'get_with_hash', _get_with_hash)

import user
import experiment
import appstate
import mapobject
import tool
import serialize
