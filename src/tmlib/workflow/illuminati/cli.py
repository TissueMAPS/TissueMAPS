import logging

from tmlib.utils import same_docstring_as
from tmlib.workflow.illuminati import logo
from tmlib.workflow.illuminati.api import PyramidBuilder
from tmlib.workflow.cli import CommandLineInterface

logger = logging.getLogger(__name__)


class Illuminati(CommandLineInterface):

    def __init__(self, api_instance, verbosity):
        '''
        Parameters
        ----------
        api_instance: tmlib.workflow.illuminati.PyramidBuilder
            instance of API class to which processing is delegated
        verbosity: int
            logging level
        '''
        super(Illuminati, self).__init__(api_instance, verbosity)

    @staticmethod
    def _print_logo():
        print logo

    @staticmethod
    @same_docstring_as(CommandLineInterface.call)
    def call(name, args):
        api_instance = PyramidBuilder(args.experiment_id, args.verbosity)
        Illuminati(api_instance, args.verbosity)._call(args)
