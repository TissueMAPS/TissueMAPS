from tmlib.workflow.args import BatchArguments
from tmlib.workflow.args import SubmissionArguments
from tmlib.workflow.args import Argument
from tmlib.workflow.registry import batch_args
from tmlib.workflow.registry import submission_args


@batch_args('metaconfig')
class MetaconfigBatchArguments(BatchArguments):

    keep_zplanes = Argument(
        type=bool, default=False, help='keep individual focal planes'
    )

    regex = Argument(
        type=str,
        help='''named regular expression that defines group names
            for retrieval of metadata from image filenames
        '''
    )

    stitch_layout = Argument(
        type=str, default='zigzag_horizontal',
        choices={
            'horizontal', 'zigzag_horizontal','vertical', 'zigzag_vertical'
        },
        help='''layout of the stitched well overview mosaic image, i.e. the
            order in which images were acquired along the grid
        '''
    )

    stitch_major_axis = Argument(
        type=str, default='vertical', choices={'vertical', 'horizontal'},
        help='longer axis of the stitched well overview mosaic image'
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


@submission_args('metaconfig')
class MetaconfigSubmissionArguments(SubmissionArguments):

    pass

