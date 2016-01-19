import logging
from . import logo
from . import __version__
from .api import PyramidBuilder
from ..layer import ChannelLayer
from ..cli import CommandLineInterface
from ..experiment import Experiment

logger = logging.getLogger(__name__)


class Illuminati(CommandLineInterface):

    def __init__(self, experiment, verbosity, level):
        '''
        Initialize an instance of class Illuminati.

        Parameters
        ----------
        experiment: tmlib.experiment.Experiment
            configured experiment object
        verbosity: int
            logging level
        level: int
            zero-based pyramid level index, where 0 represents the top pyramid
            level, i.e. the most zoomed out level with the lowest resolution
        '''
        super(Illuminati, self).__init__(experiment, verbosity)
        self.experiment = experiment
        self.verbosity = verbosity
        self.level = level

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
                    verbosity=self.verbosity,
                    level=self.level)

    def collect(self, args):
        raise AttributeError('"%s" object doesn\'t have a "collect" method'
                             % self.__class__.__name__)

    def init(self, args):
        '''
        Initialize an instance of the API class corresponding to the program
        and process arguments provided by the "init" subparser, which creates
        the job descriptor files required for submission.

        Parameters
        ----------
        args: tmlib.args.InitArgs
            method-specific arguments
        '''
        logger.info('initialize jobs for base level')
        super(Illuminati, self).init(args)

        layer = ChannelLayer(self.experiment, 0, 0, 0)
        for level in reversed(range(layer.base_level_index)):
            logger.info('initialize jobs for level # %d', level)
            cli = Illuminati(self.experiment, self.verbosity, level)
            super(Illuminati, cli).init(args)

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
        experiment = Experiment(args.experiment_dir, library='numpy')
        if args.method_name == 'run' or args.method_name == 'log':
            cli = Illuminati(experiment, args.verbosity, args.level)
        else:
            layer = ChannelLayer(experiment, 0, 0, 0)
            level = layer.base_level_index
            cli = Illuminati(experiment, args.verbosity, level)
        cli._call(args)
        if args.method_name == 'submit':
            for level in reversed(range(layer.base_level_index)):
                cli = Illuminati(experiment, args.verbosity, level)
                cli.submit(args)
