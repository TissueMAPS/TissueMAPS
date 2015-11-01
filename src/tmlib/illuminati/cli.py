import logging
from . import logo
from . import __version__
from .api import PyramidBuilder
from ..cli import CommandLineInterface
from ..experiment import Experiment

logger = logging.getLogger(__name__)


class Illuminati(CommandLineInterface):

    def __init__(self, experiment, verbosity):
        '''
        Initialize an instance of class Illuminati.

        Parameters
        ----------
        experiment: tmlib.experiment.Experiment
            configured experiment object
        verbosity: int
            logging level
        '''
        super(Illuminati, self).__init__(experiment, verbosity)
        self.experiment = experiment
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
        return PyramidBuilder(
                    experiment=self.experiment,
                    prog_name=self.name,
                    verbosity=self.verbosity)

    def collect(self, args):
        raise AttributeError('"%s" object doesn\'t have a "collect" method'
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
        :py:mod:`tmlib.illuminati.argparser`
        '''
        experiment = Experiment(args.experiment_dir)
        cli = Illuminati(experiment, args.verbosity)
        cli._call(args)
