import logging

from tmlib.utils import notimplemented
from tmlib.utils import assert_type
from tmlib.workflow.imextract import logo
from tmlib.workflow.cli import CommandLineInterface

logger = logging.getLogger(__name__)


class Imextract(CommandLineInterface):

    '''Extract pixel elements from heterogeneous microscopy image file formats
    and store each 2D pixel plane in a standardized file format.
    '''

    @assert_type(api_instance='tmlib.workflow.imextract.api.ImageExtractor')
    def __init__(self, api_instance):
        '''
        Parameters
        ----------
        api_instance: tmlib.workflow.metaextract.api.ImageExtractor
            instance of API class to which processing is delegated
        '''
        super(Imextract, self).__init__(api_instance)

    @staticmethod
    def _print_logo():
        print logo

    @notimplemented
    def collect(self, args):
        pass

