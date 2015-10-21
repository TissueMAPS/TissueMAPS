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

    def __init__(self, args):
        '''
        Initialize an instance of class Metaconfig.

        Parameters
        ----------
        args: arparse.Namespace
            parsed command line arguments
        '''
        super(Metaconfig, self).__init__(args)
        self.args = args

    @staticmethod
    def print_logo():
        print logo % {'version': __version__}

    @property
    def name(self):
        '''
        Returns
        -------
        st
            name of the program
        '''
        return self.__class__.__name__.lower()

    @property
    def _variable_init_args(self):
        kwargs = dict()
        kwargs['format'] = self.args.format
        kwargs['z_stacks'] = self.args.format
        kwargs['regex'] = self.args.regex
        kwargs['stitch_layout'] = self.args.stitch_layout
        kwargs['stitch_major_axis'] = self.args.stitch_major_axis
        kwargs['stitch_vertical'] = self.args.stitch_vertical
        kwargs['stitch_horizontal'] = self.args.stitch_horizontal
        return kwargs

    @property
    def _api_instance(self):
        logger.debug('parsed arguments: {0}'.format(self.args))
        experiment = Experiment(self.args.experiment_dir)
        self.__api_instance = MetadataConfigurator(
                            experiment=experiment, prog_name=self.name,
                            verbosity=self.args.verbosity)
        logger.debug(
            'instantiated API class "%s" with parsed arguments'
            % self.__api_instance.__class__.__name__)
        return self.__api_instance

    @staticmethod
    def call(args):
        '''
        Initializes an instance of class Metaconfig and calls the method
        that matches the name of the subparser with the parsed command
        line arguments.

        Parameters
        ----------
        args: arparse.Namespace
            parsed command line arguments
        '''
        cli = Metaconfig(args)
        logger.debug('call "%s" method of class "%s"'
                     % (args.method_name, cli.__class__.__name__))
        getattr(cli, args.method_name)()
