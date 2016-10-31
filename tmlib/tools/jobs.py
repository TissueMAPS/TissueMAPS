import logging
from tmlib.jobs import Job

logger = logging.getLogger(__name__)


class ToolJob(Job):

    '''Class for a tool job, which can be submitted to a cluster for
    asynchronous processing of a client request.
    '''

    def __init__(self, tool_name, arguments, output_dir,
            submission_id, user_name):
        '''
        Parameters
        ----------
        tool_name: str
            name of the respective tool
        arguments: List[str]
            command line arguments
        output_dir: str
            absolute path to the output directory, where log reports will
            be stored
        submission_id: int
            ID of the corresponding submission
        user_name: str
            name of the submitting user
        '''
        self.tool_name = tool_name
        super(ToolJob, self).__init__(
            arguments, output_dir, submission_id, user_name
        )

    @property
    def name(self):
        '''str:name of the job'''
        return 'tool_%s' % self.tool_name

