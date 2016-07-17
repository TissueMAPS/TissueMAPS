from tmlib.workflow.args import BatchArguments
from tmlib.workflow.args import SubmissionArguments
from tmlib.workflow.args import Argument
from tmlib.workflow import register_batch_args
from tmlib.workflow import register_submission_args


@register_batch_args('imextract')
class ImextractBatchArguments(BatchArguments):

    batch_size = Argument(
        type=int, default=10, flag='b'
        help='number of image acquisition sites to process per job',
    )


@register_submission_args('imextract')
class ImextractSubmissionArguments(SubmissionArguments):

    pass
