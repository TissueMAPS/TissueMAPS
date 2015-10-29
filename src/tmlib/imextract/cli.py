import logging
from . import logo
from . import __version__
from .api import ImageExtractor
from ..cli import CommandLineInterface
from ..experiment import Experiment

logger = logging.getLogger(__name__)


class Imextract(CommandLineInterface):

    '''
    Command line interface for extraction of images from image files.
    '''

    def __init__(self, args):
        '''
        Initialize an instance of class Imextract.

        Parameters
        ----------
        args: argparse.Namespace
            parsed command line arguments

        Returns
        -------
        tmlib.imextract.cli.Imextract
        '''
        super(Imextract, self).__init__(args)
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
        return ImageExtractor(
                experiment=experiment,
                prog_name=self.name,
                verbosity=self.args.verbosity)

    @property
    def init_args(self):
        '''
        Returns
        -------
        dict
            additional variable arguments for the `init` method

        See also
        --------
        :mod:`tmlib.imextract.argparser`
        '''
        kwargs = dict()
        kwargs['batch_size'] = self.args.batch_size
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
        :mod:`tmlib.imextract.argparser`
        '''
        cli = Imextract(args)
        logger.debug('call "%s" method of class "%s"'
                     % (args.method_name, cli.__class__.__name__))
        getattr(cli, args.method_name)()
