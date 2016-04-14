import logging

from tmlib.utils import assert_type
from tmlib.workflow.align import logo
from tmlib.workflow.cli import CommandLineInterface
from tmlib.workflow.align.args import AlignBatchArguments
from tmlib.workflow.align.args import AlignSubmissionArguments

logger = logging.getLogger(__name__)


class Align(CommandLineInterface):

    '''Register images of different multiplexing cycles relative to a
    reference cycle.
    '''

    @assert_type(api_instance='tmlib.workflow.align.api.ImageRegistrator')
    def __init__(self, api_instance):
        '''
        Parameters
        ----------
        api_instance: tmlib.workflow.align.api.ImageRegistrator
            instance of API class to which processing is delegated 
        '''
        super(Align, self).__init__(api_instance)

    @staticmethod
    def _print_logo():
        print logo
