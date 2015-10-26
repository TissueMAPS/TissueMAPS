import logging
from . import logo
from . import __version__
from .api import PyramidBuilder
from ..cli import CommandLineInterface
from ..experiment import Experiment

logger = logging.getLogger(__name__)


class Illuminati(CommandLineInterface):

    def __init__(self, args):
        '''
        Initialize an instance of class illuminati.

        Parameters
        ----------
        args: argparse.Namespace
            parsed command line arguments

        Returns
        -------
        tmlib.illuminati.cli.Illuminati
        '''
        super(Illuminati, self).__init__(args)
        self.args = args

    @staticmethod
    def print_logo():
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
        experiment = Experiment(self.args.experiment_dir)
        self.__api_instance = PyramidBuilder(
                                experiment=experiment, prog_name=self.name,
                                verbosity=self.args.verbosity)
        return self.__api_instance

    @property
    def _init_args(self):
        kwargs = dict()
        kwargs['shift'] = self.args.shift
        kwargs['illumcorr'] = self.args.illumcorr
        kwargs['thresh'] = self.args.thresh
        kwargs['thresh_value'] = self.args.thresh_value
        kwargs['thresh_percent'] = self.args.thresh_percent
        return kwargs

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
        `tmlib.illuminati.argparser`_
        '''
        cli = Illuminati(args)
        logger.debug('call "%s" method of class "%s"'
                     % (args.method_name, cli.__class__.__name__))
        getattr(cli, args.method_name)()
