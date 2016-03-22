import logging
from . import logo
from .api import MetadataExtractor
from ..cli import CommandLineInterface

logger = logging.getLogger(__name__)


class Metaextract(CommandLineInterface):

    '''
    Command line interface for extraction of metadata from image files.
    '''

    def __init__(self, experiment, verbosity):
        '''
        Parameters
        ----------
        experiment: tmlib.models.Experiment
            experiment that should be processed
        verbosity: int
            logging level
        '''
        super(Metaextract, self).__init__(experiment, verbosity)

    @staticmethod
    def _print_logo():
        print logo

    @property
    def _api_instance(self):
        return MetadataExtractor(
                    self.experiment, self.name, self.verbosity)

    def run(self, args):
        raise AttributeError('"%s" object doesn\'t have a "run" method'
                             % self.__class__.__name__)

    @staticmethod
    def call(args, experiment):
        '''
        Initialize an instance of the cli class with the parsed command
        line arguments and call the method matching the name of the subparser.

        Parameters
        ----------
        args: arparse.Namespace
            parsed command line arguments
        experiment: tmlib.models.Experiment
            experiment that should be processed

        See also
        --------
        :py:mod:`tmlib.metaextract.argparser`
        '''
        Metaextract(experiment, args.verbosity)._call(args)
