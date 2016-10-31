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
import numpy as np
from sqlalchemy import Integer, Column, String

from tmlib.models import ExperimentModel

logger = logging.getLogger(__name__)


class ToolResult(ExperimentModel):

    '''A tool result bundles all elements that should be visualized together
    client side.

    Attributes
    ----------
    layer: tmlib.tools.result.LabelLayer
        client-side map representation of a tool result
    plots: List[tmlib.tools.result.Plot]
        all plots linked to the label `layer`
    '''

    __tablename__ = 'tool_results'

    #: str: name of the result given by the user
    name = Column(String(50), index=True)

    #: str: name of the corresponding tool
    tool_name = Column(String(30), index=True)

    #: int: ID of the corresponding job submission
    submission_id = Column(Integer, index=True)

    def __init__(self, submission_id, tool_name, name=None):
        '''A persisted result that can be interpreted and visualized by the
        client.

        Parameters
        ----------
        submission_id: int
            ID of the respective job submission
        tool_name: str
            name of the tool that generated the result
        name: str, optional
            a descriptive name for this result
        '''
        if name is None:
            self.name = '%s-%d result' % (tool_name, submission_id)
        else:
            self.name = name
        self.tool_name = tool_name
        self.submission_id = submission_id



