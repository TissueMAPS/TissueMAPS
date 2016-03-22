import logging
from . import logo
from . import __version__
from .api import MetadataConfigurator
from ..cli import CommandLineInterface
from ..experiment import Experiment

logger = logging.getLogger(__name__)


class Metaconfig(CommandLineInterface):

    '''
    Command line interface for metadata conversion.
    '''

    def __init__(self, experiment, verbosity, **kwargs):
        '''
        Initialize an instance of class Metaconfig.

        Parameters
        ----------
        experiment: tmlib.experiment.Experiment
            configured experiment object
        verbosity: int
            logging level
        kwargs: dict
            mapping of additional key-value pairs that are ignored
        '''
        super(Metaconfig, self).__init__(experiment, verbosity)

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
    def _api_instance(self, **kwargs):
        return MetadataConfigurator(
                    self.experiment, self.name, self.verbosity)

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
        :py:mod:`tmlib.metaconfig.argparser`
        '''
        experiment = Experiment(args.experiment_dir)
        cli = Metaconfig(experiment, args.verbosity)
        cli._call(args)
