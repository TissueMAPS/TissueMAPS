import logging

from tmlib.utils import same_docstring_as
from tmlib.workflow.align import logo
from tmlib.workflow.align.api import ImageRegistration
from tmlib.workflow.cli import CommandLineInterface

logger = logging.getLogger(__name__)


class Align(CommandLineInterface):

    def __init__(self, api_instance, verbosity):
        '''
        Initialize an instance of class Align.

        Parameters
        ----------
        api_instance: tmlib.workflow.align.ImageRegistration
            configured experiment object
        verbosity: int
            logging level
        '''
        super(Align, self).__init__(api_instance, verbosity)

    @staticmethod
    def _print_logo():
        print logo

    @staticmethod
    @same_docstring_as(CommandLineInterface.call)
    def call(name, args):
        api_instance = ImageRegistration(
            args.experiment_id, name, args.verbosity
        )
        Align(api_instance, args.verbosity)._call(args)
