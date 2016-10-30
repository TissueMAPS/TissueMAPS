# TmServer - TissueMAPS server application.
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
from tmlib.workflow.jobs import Job

logger = logging.getLogger(__name__)


class ToolJob(Job):

    '''Class for a tool job, which can be submitted to a cluster for
    asynchronous processing of the client tool request.
    '''

    def __init__(self, tool_name, arguments, output_dir,
            submission_id, user_name):
        self.tool_name = tool_name
        super(ToolJob, self).__init__(
            self.name, arguments, output_dir, submission_id, user_name
        )

    @property
    def name(self):
        return 'tool_%s' % self.tool_name


