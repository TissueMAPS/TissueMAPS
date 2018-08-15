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
from tmlib.workflow.args import BatchArguments
from tmlib.workflow.args import SubmissionArguments
from tmlib.workflow.args import Argument
from tmlib.workflow import register_step_batch_args
from tmlib.workflow import register_step_submission_args


@register_step_batch_args('imextract')
class ImextractBatchArguments(BatchArguments):

    batch_size = Argument(
        type=int, default=100, flag='batch-size', short_flag='b',
        help='number of image acquisition sites to process per job',
    )

    delete = Argument(
        type=bool, default=False,
        help='''
            delete microscope files after pixel data got extracted
            (Warning: You won't be able to rerun jobs afterwards!)
        '''
    )


@register_step_submission_args('imextract')
class ImextractSubmissionArguments(SubmissionArguments):

    pass
