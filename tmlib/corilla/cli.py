import logging
from . import logo
from . import __version__
from .api import IllumstatsGenerator
from ..cli import CommandLineInterface
from ..experiment import ExperimentFactory

logger = logging.getLogger(__name__)


class Corilla(CommandLineInterface):

    def __init__(self, args):
        super(Corilla, self).__init__(args)
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
            name of the program
        '''
        return self.__class__.__name__.lower()

    @property
    def _api_instance(self):
        logger.debug('parsed arguments: {0}'.format(self.args))
        experiment = ExperimentFactory(self.args.experiment_dir).create()
        self.__api_instance = IllumstatsGenerator(
                                experiment=experiment, prog_name=self.name,
                                verbosity=self.args.verbosity)
        logger.debug(
            'instantiated API class "%s" with parsed arguments'
            % self.__api_instance.__class__.__name__)
        return self.__api_instance

    @property
    def _variable_apply_args(self):
        kwargs = dict()
        kwargs['plates'] = self.args.plates
        kwargs['wells'] = self.args.wells
        kwargs['channels'] = self.args.channels
        kwargs['zplanes'] = self.args.zplanes
        kwargs['tpoints'] = self.args.tpoints
        return kwargs

    @staticmethod
    def call(args):
        '''
        Calls the method that matches the name of the specified subparser with
        the parsed command line arguments.

        Parameters
        ----------
        args: arparse.Namespace
            parsed command line arguments

        See also
        --------
        `tmlib.corilla.argparser`_
        '''
        cli = Corilla(args)
        logger.debug('call "%s" method of class "%s"'
                     % (args.method_name, cli.__class__.__name__))
        getattr(cli, args.method_name)()
