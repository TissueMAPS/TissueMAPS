import logging

from tmlib.utils import notimplemented
from tmlib.utils import assert_type
from tmlib.workflow.metaextract import logo
from tmlib.workflow.cli import CommandLineInterface

logger = logging.getLogger(__name__)


class Metaextract(CommandLineInterface):

    '''Extract OMEXML metadata from heterogeneous microscopy image file formats.
    '''

    @assert_type(api_instance='tmlib.workflow.metaextract.api.MetadataExtractor')
    def __init__(self, api_instance):
        '''
        Parameters
        ----------
        api_instance: tmlib.workflow.metaextract.api.MetadataExtractor
            instance of API class to which processing is delegated
        '''
        super(Metaextract, self).__init__(api_instance)

    @staticmethod
    def _print_logo():
        print logo

    @notimplemented
    def collect(self, args):
        pass
