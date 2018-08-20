# TmServer - TissueMAPS server application.
# Copyright (C) 2016-2018 University of Zurich.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import sqlalchemy.orm

from tmlib.models import MainModel, ExperimentModel
from tmserver.model.utils import *


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
setattr(ExperimentModel, 'hash', _monkeypatched_hash_property)
setattr(MainModel, 'hash', _monkeypatched_hash_property)
