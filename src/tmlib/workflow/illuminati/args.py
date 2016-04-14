from tmlib.workflow.args import Argument
from tmlib.workflow.args import BatchArguments
from tmlib.workflow.args import SubmissionArguments
from tmlib.workflow.registry import batch_args
from tmlib.workflow.registry import submission_args


@batch_args('illuminati')
class IlluminatiBatchArguments(BatchArguments):

    batch_size = Argument(
        type=int, default=10, flag='b',
        help='number of image files that should be processed per job'
    )

    align = Argument(
        type=bool, default=False, flag='a',
        help='whether images should be aligned between multiplexing cycles'
    )

    illumcorr = Argument(
        type=bool, default=False, flag='i',
        help='wether images should be corrected for illumination artifacts'
    )

    clip = Argument(
        type=bool, default=False, flag='c',
        help='whether images intensities should be clipped'
    )

    clip_value = Argument(
        type=int,
        help='''threshold value at which image intensities should be clipped
            (defaults to 99.999th percentile)
        '''
    )


@submission_args('illuminati')
class IlluminatiSubmissionArguments(SubmissionArguments):

    pass
