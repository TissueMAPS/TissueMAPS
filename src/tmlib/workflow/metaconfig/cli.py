import logging

from tmlib.utils import same_docstring_as
from tmlib.workflow.metaconfig import logo
from tmlib.workflow.metaconfig.api import MetadataConfigurator
from tmlib.workflow.cli import CommandLineInterface

logger = logging.getLogger(__name__)


class Metaconfig(CommandLineInterface):

    '''Command line interface for metadata conversion.'''

    def __init__(self, api_instance, verbosity):
        '''
        Parameters
        ----------
        api_instance: tmlib.workflow.metaconfig.MetadataConfigurator
            instance of API class to which processing is delegated
        verbosity: int
            logging level
        '''
        super(Metaconfig, self).__init__(api_instance, verbosity)

    @staticmethod
    def _print_logo():
        print logo

    @staticmethod
    @same_docstring_as(CommandLineInterface.call)
    def call(name, args):
        api_instance = MetadataConfigurator(args.experiment_id, args.verbosity)
        Metaconfig(api_instance, args.verbosity)._call(args)
