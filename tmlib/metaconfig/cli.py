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

        Returns
        -------
        tmlib.metaconfig.cli.Metaconfig
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
            name of the command line program
        '''
        return self.__class__.__name__.lower()

    @property
    def _init_args(self):
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
        experiment = Experiment(self.args.experiment_dir)
        return MetadataConfigurator(
                            experiment=experiment, prog_name=self.name,
                            verbosity=self.args.verbosity)

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
        `tmlib.metaconfig.argparser`_
        '''
        cli = Metaconfig(args)
        logger.debug('call "%s" method of class "%s"'
                     % (args.method_name, cli.__class__.__name__))
        getattr(cli, args.method_name)()
