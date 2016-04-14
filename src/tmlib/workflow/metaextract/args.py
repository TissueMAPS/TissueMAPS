from tmlib.workflow.args import Argument
from tmlib.workflow.args import BatchArguments
from tmlib.workflow.args import SubmissionArguments
from tmlib.workflow.registry import batch_args
from tmlib.workflow.registry import submission_args

@batch_args('metaextract')
class MetaextractBatchArguments(BatchArguments):

    batch_size = Argument(
        type=int, help='number of images that should be processed per job',
        default=10, flag='b'
    )

@submission_args('metaextract')
class MetaextractSubmissionArguments(SubmissionArguments):
    pass 
