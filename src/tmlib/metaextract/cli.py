import logging
from . import logo
from . import __version__
from .api import MetadataExtractor
from ..cli import CommandLineInterface
from ..experiment import Experiment

logger = logging.getLogger(__name__)


class Metaextract(CommandLineInterface):

    '''
    Command line interface for extraction of metadata from image files.
    '''

    def __init__(self, experiment, verbosity, **kwargs):
        '''
        Initialize an instance of class Metaextract.

        Parameters
        ----------
        experiment: tmlib.experiment.Experiment
            configured experiment object
        verbosity: int
            logging level
        kwargs: dict
            additional key-value pairs that are ignored
        '''
        super(Metaextract, self).__init__(experiment, verbosity)

    @staticmethod
    def _print_logo():
        print logo % {'version': __version__}

    @property
    def name(self):
        '''
        Returns
        -------
        str
            name of the command line program
        '''
        return self.__class__.__name__.lower()

    @property
    def _api_instance(self):
        return MetadataExtractor(
                    self.experiment, self.name, self.verbosity)

    def run(self, args):
        raise AttributeError('"%s" object doesn\'t have a "run" method'
                             % self.__class__.__name__)

    @staticmethod
    def call(args):
        '''
        Initialize an instance of the cli class with the parsed command
        line arguments and call the method matching the name of the subparser.

        Parameters
        ----------
        args: arparse.Namespace
            parsed command line arguments

        See also
        --------
        :py:mod:`tmlib.metaextract.argparser`
        '''
        experiment = Experiment(args.experiment_dir)
        Metaextract(experiment, args.verbosity)._call(args)
