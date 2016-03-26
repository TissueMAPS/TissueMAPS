import logging

from tmlib.utils import same_docstring_as
from tmlib.workflow.corilla import logo
from tmlib.workflow.corilla.api import IllumstatsGenerator
from tmlib.workflow.cli import CommandLineInterface

logger = logging.getLogger(__name__)


class Corilla(CommandLineInterface):

    '''Command line interface for calculating illumination statistics
    across all images of the same channel.


    These statistics can then be used to correct channel images for
    illumination artifacts.
    '''

    def __init__(self, api_instance, verbosity, **kwargs):
        '''
        Parameters
        ----------
        api_instance: tmlib.workflow.corilla.IllumstatsGenerator
            instance of API class to which processing is delegated
        verbosity: int
            logging level
        kwargs: dict
            additional key-value pairs that are ignored
        '''
        super(Corilla, self).__init__(api_instance, verbosity)

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
        api_instance = IllumstatsGenerator(
            args.experiment_id, name, args.verbosity
        )
        Corilla(api_instance, args.verbosity)._call(args)
