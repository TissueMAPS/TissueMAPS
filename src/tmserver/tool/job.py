import logging
from tmlib.workflow.jobs import Job

logger = logging.getLogger(__name__)


class ToolJob(Job):

    '''Class for a tool job, which can be submitted to a cluster for
    asynchronous processing of the client tool request.
    '''

    def __init__(self, tool_name, arguments, output_dir,
            submission_id, user_name):
        self.tool_name = tool_name
        super(ToolJob, self).__init__(
            arguments, output_dir, submission_id, user_name
        )

    @property
    def name(self):
        return 'tool_%s' % self.tool_name


