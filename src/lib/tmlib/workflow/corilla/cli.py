import logging

from tmlib.utils import notimplemented
from tmlib.utils import assert_type
from tmlib.workflow.cli import CommandLineInterface

logger = logging.getLogger(__name__)


class Corilla(CommandLineInterface):

    @assert_type(api_instance='tmlib.workflow.corilla.api.IllumstatsCalculator')
    def __init__(self, api_instance):
        '''
        Parameters
        ----------
        api_instance: tmlib.workflow.corilla.api.IllumstatsCalculator
            instance of API class to which processing is delegated
        '''
        super(Corilla, self).__init__(api_instance)

    @notimplemented
    def collect(self, args):
        pass
