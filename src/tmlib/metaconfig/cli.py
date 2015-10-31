import logging
from . import logo
from . import __version__
from .api import MetadataConfigurator
from ..cli import CommandLineInterface

logger = logging.getLogger(__name__)


class Metaconfig(CommandLineInterface):

    '''
    Command line interface for metadata conversion.
    '''

    def __init__(self, experiment_dir, verbosity):
        '''
        Initialize an instance of class Metaconfig.

        Parameters
        ----------
        experiment_dir: str
            path to the experiment directory
        verbosity: int
            logging level
        '''
        super(Metaconfig, self).__init__(experiment_dir, verbosity)
        self.experiment_dir = experiment_dir
        self.verbosity = verbosity

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
        return MetadataConfigurator(
                    experiment=self.experiment,
                    prog_name=self.name,
                    verbosity=self.verbosity)

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
        cli = Metaconfig(args.experiment_dir, args.verbosity)
        cli._call(args)
