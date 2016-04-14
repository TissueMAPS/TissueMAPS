from tmlib.workflow.args import BatchArguments
from tmlib.workflow.args import SubmissionArguments
from tmlib.workflow.args import Argument
from tmlib.workflow.registry import batch_args
from tmlib.workflow.registry import submission_args


@batch_args('align')
class AlignBatchArguments(BatchArguments):

    ref_cycle = Argument(
        type=int, required=True, flag='c',
        help='''zero-based index of the cycle whose sites should be used
            as reference
        '''
    )

    ref_wavelength = Argument(
        type=str, required=True, flag='w',
        help='name of the wavelength whose images should be used as reference'
    )

    batch_size = Argument(
        type=int, default=10, flag='b',
        help='number of image files that should be processed per job'
    )


@submission_args('align')
class AlignSubmissionArguments(SubmissionArguments):

    pass
