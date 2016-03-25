import logging

from tmlib.utils import same_docstring_as
from tmlib.workflow.metaextract import logo
from tmlib.workflow.metaextract.api import MetadataExtractor
from tmlib.workflow.cli import CommandLineInterface

logger = logging.getLogger(__name__)


class Metaextract(CommandLineInterface):

    '''
    Command line interface for extraction of metadata from
    microscope image files.
    '''

    def __init__(self, api_instance, verbosity):
        '''
        Parameters
        ----------
        api_instance: tmlib.workflow.metaextract.MetadataExtractor
            instance of API class to which processing is delegated
        verbosity: int
            logging level
        '''
        super(Metaextract, self).__init__(api_instance, verbosity)

    @staticmethod
    def _print_logo():
        print logo

    def run(self, args):
        raise AttributeError(
            '"%s" object doesn\'t have a "run" method'
            % self.__class__.__name__
        )

    @staticmethod
    @same_docstring_as(CommandLineInterface.call)
    def call(name, args):
        api_instance = MetadataExtractor(
            args.experiment_id, name, args.verbosity
        )
        Metaextract(api_instance, args.verbosity)._call(args)
