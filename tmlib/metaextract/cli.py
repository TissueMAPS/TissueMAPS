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

    def __init__(self, args):
        '''
        Initialize an instance of class Metaextract.

        Parameters
        ----------
        args: arparse.Namespace
            parsed command line arguments

        Returns
        -------
        tmlib.metaconfig.cli.Metaextract
        '''
        super(Metaextract, self).__init__(args)
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
        logger.debug('parsed arguments: {0}'.format(self.args))
        experiment = Experiment(self.args.experiment_dir)
        self.__api_instance = MetadataExtractor(
                                experiment=experiment, prog_name=self.name,
                                verbosity=self.args.verbosity)
        logger.debug(
            'instantiated API class "%s" with parsed arguments'
            % self.__api_instance.__class__.__name__)
        return self.__api_instance

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
        :mod:`tmlib.metaextract.argparser`
        '''
        cli = Metaextract(args)
        getattr(cli, args.method_name)()
