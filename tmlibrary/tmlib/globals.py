# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2018  University of Zurich
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
"""
Library-wide objects and state.
"""

# stdlib imports

# 3rd party imports
from gc3libs.persistence.sql import IdFactory, IntId

# local imports


def _postgresql_next_task_id(n=1):
    """
    Return the next object ID for the ``tasks`` table.

    This function leverages PostgreSQL's sequence support, which makes
    it safe against multi-threading and multi-process usage.
    """
    import tmlib.models.utils as tmu
    with tmu.MainSession() as db:
        q = db.execute("SELECT nextval('tasks_id_seq');")
        return q.fetchone()[0]

idfactory = IdFactory(
    next_id_fn=_postgresql_next_task_id,
    id_class=IntId)
"""
Generate unique persistent IDs for GC3Pie.

The default value uses PostGreSQL's ``nextval`` function to fetch the
next sequential ID for the ``tasks`` table in TM's main DB.
"""
