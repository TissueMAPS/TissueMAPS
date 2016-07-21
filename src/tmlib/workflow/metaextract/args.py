from tmlib.workflow.args import Argument
from tmlib.workflow.args import BatchArguments
from tmlib.workflow.args import SubmissionArguments
from tmlib.workflow import register_batch_args
from tmlib.workflow import register_submission_args


@register_batch_args('metaextract')
class MetaextractBatchArguments(BatchArguments):

    batch_size = Argument(
        type=int, help='number of images that should be processed per job',
        default=100, flag='b'
    )


@register_submission_args('metaextract')
class MetaextractSubmissionArguments(SubmissionArguments):
    pass 
