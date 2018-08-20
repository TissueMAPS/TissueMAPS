# TmLibrary - TissueMAPS library for distibuted image analysis routines.
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
from tmlib.workflow.args import BatchArguments
from tmlib.workflow.args import SubmissionArguments
from tmlib.workflow.args import Argument
from tmlib.workflow import register_step_batch_args
from tmlib.workflow import register_step_submission_args


@register_step_batch_args('align')
class AlignBatchArguments(BatchArguments):

    ref_cycle = Argument(
        type=int, required=True, flag='ref-cycle', short_flag='c',
        help='''zero-based index of the cycle whose sites should be used
            as reference
        '''
    )

    ref_wavelength = Argument(
        type=str, required=True, flag='ref-wavelength', short_flag='w',
        help='name of the wavelength whose images should be used as reference'
    )

    batch_size = Argument(
        type=int, default=100, flag='batch-size', short_flag='b',
        help='number of acquisition sites that should be processed per job'
    )

    illumcorr = Argument(
        type=bool, default=False, short_flag='i',
        help='whether images should be corrected for illumination artifacts'
    )

    robust_align = Argument(
        type=bool, default=False, short_flag='r',
        help='''whether pixel intensities are clipped to the specified percentile 
             to avoid artefacts (dirt may be small but have a high intensity. 
             Clipping its value stops it from distorting the alignment)'''
    )

    rescale_percentile = Argument(
        type=float, default=99.90, flag='clip-percent',
        help='''threshold percentile at which image intensities should be 
             clipped if robust_align is selected'''
    )


@register_step_submission_args('align')
class AlignSubmissionArguments(SubmissionArguments):

    pass
