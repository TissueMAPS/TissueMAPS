import logging
from . import logo
from . import __version__
from .api import ImageRegistration
from ..cli import CommandLineInterface

logger = logging.getLogger(__name__)


class Align(CommandLineInterface):

    def __init__(self, experiment_dir, verbosity):
        '''
        Initialize an instance of class Align.

        Parameters
        ----------
        experiment_dir: str
            path to the experiment directory
        verbosity: int
            logging level
        '''
        super(Align, self).__init__(experiment_dir, verbosity)
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
        return ImageRegistration(
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
        :py:mod:`tmlib.align.argparser`
        '''
        cli = Align(args.experiment_dir, args.verbosity)
        cli._call(args)
