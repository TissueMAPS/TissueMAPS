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

from tmlib.workflow.jobs import RunJob

logger = logging.getLogger(__name__)


class DebugRunJob(RunJob):

    '''Class for TissueMAPS debug jobs, which can be processed in parallel.'''

    def __init__(self, step_name, arguments, output_dir, job_id,
                 submission_id, user_name):
        '''
        Parameters
        ----------
        step_name: str
            name of the corresponding TissueMAPS workflow step
        arguments: List[str]
            command line arguments
        output_dir: str
            absolute path to the output directory, where log reports will
            be stored
        job_id: int
            one-based job identifier number
        submission_id: int
            ID of the corresponding submission
        '''
        super(DebugRunJob, self).__init__(
            step_name=step_name,
            arguments=arguments,
            output_dir=output_dir,
            job_id=job_id,
            submission_id=submission_id,
            user_name=user_name
        )

    @property
    def name(self):
        '''str: name of the job'''
        if self.index is None:
            return '%s_debug-run_%.6d' % (self.step_name, self.job_id)
        else:
            return (
                '%s_debug-run-%.2d_%.6d' % (
                    self.step_name, self.index, self.job_id
                )
            )
