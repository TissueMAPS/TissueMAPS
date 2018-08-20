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


@register_step_batch_args('metaconfig')
class MetaconfigBatchArguments(BatchArguments):

    regex = Argument(
        type=str,
        help='''named regular expression that defines group names
            for retrieval of metadata from image filenames
        '''
    )

    stitch_layout = Argument(
        type=str, default='horizontal',
        choices={
            'horizontal', 'zigzag_horizontal','vertical', 'zigzag_vertical'
        },
        help='''layout of the stitched well overview mosaic image, i.e. the
            order in which images were acquired along the grid
        '''
    )

    n_vertical = Argument(
        type=int,
        help='''number of images along the vertical axis of the stitched well
            overview mosaic image
        '''
    )

    n_horizontal = Argument(
        type=int,
        help='''number of images along the horizontal axis of the stitched well
            overview mosaic image
        '''
    )

    mip = Argument(
        type=bool, default=False,
        help='perform maximum intensity projection along z axis'
    )


@register_step_submission_args('metaconfig')
class MetaconfigSubmissionArguments(SubmissionArguments):

    pass

