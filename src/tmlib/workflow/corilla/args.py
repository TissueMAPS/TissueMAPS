from tmlib.workflow.args import BatchArguments
from tmlib.workflow.args import SubmissionArguments
from tmlib.workflow.registry import batch_args
from tmlib.workflow.registry import submission_args


@batch_args('corilla')
class CorillaBatchArguments(BatchArguments):

    pass


@submission_args('corilla')
class CorillaSubmissionArguments(SubmissionArguments):

    pass
