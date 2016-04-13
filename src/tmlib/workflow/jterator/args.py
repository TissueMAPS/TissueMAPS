from tmlib.workflow.args import Argument
from tmlib.workflow.args import BatchArguments
from tmlib.workflow.args import SubmissionArguments
from tmlib.workflow.registry import batch_args
from tmlib.workflow.registry import submission_args


@batch_args('jterator')
class JteratorBatchArguments(BatchArguments):

    plot = Argument(
        type=bool, default=False, flag='p',
        help='whether plotting should be activated'
    )


@submission_args('jterator')
class JteratorSubmissionArguments(SubmissionArguments):

    pass
