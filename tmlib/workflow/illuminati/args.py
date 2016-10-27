from tmlib.workflow.args import Argument
from tmlib.workflow.args import BatchArguments
from tmlib.workflow.args import SubmissionArguments
from tmlib.workflow import register_batch_args
from tmlib.workflow import register_submission_args


@register_batch_args('illuminati')
class IlluminatiBatchArguments(BatchArguments):

    batch_size = Argument(
        type=int, default=100, flag='b',
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
            (defaults to 99.99th percentile; the set value overwrites
            calculated percentile)
        '''
    )

    clip_percent = Argument(
        type=float,
        help='''threshold percentile at which image intensities should be clipped
        ''',
        default=99.90
    )

@register_submission_args('illuminati')
class IlluminatiSubmissionArguments(SubmissionArguments):

    pass
