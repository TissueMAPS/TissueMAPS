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


@register_step_batch_args('illuminati')
class IlluminatiBatchArguments(BatchArguments):

    batch_size = Argument(
        type=int, default=100, flag='batch-size', short_flag='b',
        help='number of image files that should be processed per job'
    )

    align = Argument(
        type=bool, default=False, short_flag='a',
        help='whether images should be aligned between multiplexing cycles'
    )

    illumcorr = Argument(
        type=bool, default=False, short_flag='i',
        help='whether images should be corrected for illumination artifacts'
    )

    clip = Argument(
        type=bool, default=False, short_flag='c',
        help='whether images intensities should be clipped'
    )

    clip_value = Argument(
        type=int, flag='clip-value',
        help='''threshold value at which image intensities should be clipped
            (defaults to 99.99th percentile; the set value overwrites
            calculated percentile)
        '''
    )

    clip_percent = Argument(
        type=float, default=99.90, flag='clip-percent',
        help='''threshold percentile at which image intensities should be clipped
        '''
    )

    illumcorr_exceptions = Argument(
        type=str, flag='illumcorr_exceptions',
        help='''A list of comma-separated channel names that will not be
             illumination corrected. Useful when segmentation channels are
             uploaded.
        '''
    )

@register_step_submission_args('illuminati')
class IlluminatiSubmissionArguments(SubmissionArguments):

    pass
