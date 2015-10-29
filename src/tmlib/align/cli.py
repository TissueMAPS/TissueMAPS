import logging
from . import logo
from . import __version__
from .api import ImageRegistration
from ..cli import CommandLineInterface
from ..experiment import Experiment

logger = logging.getLogger(__name__)


class Align(CommandLineInterface):

    def __init__(self, args):
        '''
        Initialize an instance of class Align.

        Parameters
        ----------
        args: argparse.Namespace
            parsed command line arguments

        Returns
        -------
        tmlib.align.cli.Align
        '''
        super(Align, self).__init__(args)
        self.args = args

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
        experiment = Experiment(self.args.experiment_dir)
        return ImageRegistration(
                experiment=experiment,
                prog_name=self.name,
                verbosity=self.args.verbosity)

    @property
    def _init_args(self):
        kwargs = dict()
        kwargs['batch_size'] = self.args.batch_size
        kwargs['ref_cycle'] = self.args.ref_cycle
        kwargs['ref_channel'] = self.args.ref_channel
        kwargs['limit'] = self.args.limit
        return kwargs

    @property
    def _apply_args(self):
        kwargs = dict()
        kwargs['illumcorr'] = self.args.illumcorr
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
        :py:mod:`tmlib.align.argparser`
        '''
        cli = Align(args)
        logger.debug('call "%s" method of class "%s"'
                     % (args.method_name, cli.__class__.__name__))
        getattr(cli, args.method_name)()
