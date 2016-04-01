import logging

from tmlib.utils import same_docstring_as
from tmlib.workflow.imextract import logo
from tmlib.workflow.imextract.api import ImageExtractor
from tmlib.workflow.cli import CommandLineInterface

logger = logging.getLogger(__name__)


class Imextract(CommandLineInterface):

    '''
    Command line interface for extraction of images from image files.
    '''

    def __init__(self, api_instance, verbosity):
        '''
        Parameters
        ----------
        api_instance: tmlib.workflow.metaextract.ImageExtractor
            instance of API class to which processing is delegated
        verbosity: int
            logging level
        '''
        super(Imextract, self).__init__(api_instance, verbosity)

    @staticmethod
    def _print_logo():
        print logo

    def collect(self, args):
        raise AttributeError(
            '"%s" object doesn\'t have a "collect" method'
            % self.__class__.__name__
        )

    @staticmethod
    @same_docstring_as(CommandLineInterface.call)
    def call(name, args):
        api_instance = ImageExtractor(
            args.experiment_id, name, args.verbosity
        )
        Imextract(api_instance, args.verbosity)._call(args)
