from tmlib.workflow.args import BatchArguments
from tmlib.workflow.args import SubmissionArguments
from tmlib.workflow import register_batch_args
from tmlib.workflow import register_submission_args


@register_batch_args('corilla')
class CorillaBatchArguments(BatchArguments):

    pass


@register_submission_args('corilla')
class CorillaSubmissionArguments(SubmissionArguments):

    pass
