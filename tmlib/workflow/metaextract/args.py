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
from tmlib.workflow.args import Argument
from tmlib.workflow.args import BatchArguments
from tmlib.workflow.args import SubmissionArguments
from tmlib.workflow import register_step_batch_args
from tmlib.workflow import register_step_submission_args


@register_step_batch_args('metaextract')
class MetaextractBatchArguments(BatchArguments):

    batch_size = Argument(
        type=int, help='number of images that should be processed per job',
        default=100, flag='batch-size', short_flag='b'
    )


@register_step_submission_args('metaextract')
class MetaextractSubmissionArguments(SubmissionArguments):
    pass 
