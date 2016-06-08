from tmlib.workflow.args import Argument
from tmlib.workflow.args import BatchArguments
from tmlib.workflow.args import SubmissionArguments
from tmlib.workflow.args import ExtraArguments
from tmlib.workflow.registry import batch_args
from tmlib.workflow.registry import submission_args
from tmlib.workflow.registry import extra_args


@batch_args('jterator')
class JteratorBatchArguments(BatchArguments):

    plot = Argument(
        type=bool, default=False, flag='p', disabled=True,
        help='whether plotting should be activated'
    )


@submission_args('jterator')
class JteratorSubmissionArguments(SubmissionArguments):

    pass


@extra_args('jterator')
class JteratorExtraArguments(ExtraArguments):

    pipeline = Argument(
        type=str, help='name of the pipeline that should be processed',
        required=True, flag='p'
    )
