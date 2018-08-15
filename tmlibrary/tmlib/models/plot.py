# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
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
import logging
from sqlalchemy import Integer, ForeignKey, Column
from sqlalchemy.orm import relationship, backref
from sqlalchemy.dialects.postgresql import JSON

from tmlib.models.base import ExperimentModel, IdMixIn

logger = logging.getLogger(__name__)


class Plot(ExperimentModel, IdMixIn):

    '''A plot that can be visualized client side along with a
    :class:`tmlib.models.layer.LabelLayer`.
    '''

    __tablename__ = 'plots'

    #: dict: mapping that's interpreted by the client tool handler
    attributes = Column(JSON)

    #: int: ID of the parent tool result
    result_id = Column(
        Integer,
        ForeignKey('tool_results.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    #: tmlib.models.result.ToolResult: parent tool result
    result = relationship(
        'ToolResult',
        backref=backref('plots', cascade='all, delete-orphan')
    )

    def __init__(self, attributes, result_id):
        '''
        Parameters
        ---------
        attributes: dict
            mapping that's interpreted by the client tool handler
        result_id: int
            ID of the parent tool result

        '''
        self.attributes = attributes
        self.result_id = result_id

