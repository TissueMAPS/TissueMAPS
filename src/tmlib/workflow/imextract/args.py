from tmlib.workflow.args import BatchArguments
from tmlib.workflow.args import SubmissionArguments
from tmlib.workflow.args import Argument
from tmlib.workflow import register_batch_args
from tmlib.workflow import register_submission_args


@register_batch_args('imextract')
class ImextractBatchArguments(BatchArguments):

    batch_size = Argument(
        type=int, default=10, help='number of images to process per job',
        flag='b'
    )


@register_submission_args('imextract')
class ImextractSubmissionArguments(SubmissionArguments):

    pass
