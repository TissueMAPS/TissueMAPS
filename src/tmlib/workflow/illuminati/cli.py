import logging

from tmlib.utils import assert_type
from tmlib.workflow.illuminati import logo
from tmlib.workflow.cli import CommandLineInterface

logger = logging.getLogger(__name__)


class Illuminati(CommandLineInterface):

    '''Create image pyramids for interactive web-based visualization.'''

    @assert_type(api_instance='tmlib.workflow.illuminati.api.PyramidBuilder')
    def __init__(self, api_instance):
        '''
        Parameters
        ----------
        api_instance: tmlib.workflow.illuminati.api.PyramidBuilder
            instance of API class to which processing is delegated
        '''
        super(Illuminati, self).__init__(api_instance)

    @staticmethod
    def _print_logo():
        print logo
