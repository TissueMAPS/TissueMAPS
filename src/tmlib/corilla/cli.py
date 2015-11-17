import logging
from . import logo
from . import __version__
from .api import IllumstatsGenerator
from ..cli import CommandLineInterface
from ..experiment import Experiment

logger = logging.getLogger(__name__)


class Corilla(CommandLineInterface):

    def __init__(self, experiment, verbosity):
        '''
        Initialize an instance of class Corilla.

        Parameters
        ----------
        experiment: tmlib.experiment.Experiment
            configured experiment object
        verbosity: int
            logging level
        '''
        super(Corilla, self).__init__(experiment, verbosity)
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

    def collect(self, args):
        raise AttributeError('"%s" object doesn\'t have a "collect" method'
                             % self.__class__.__name__)

    @property
    def _api_instance(self):
        return IllumstatsGenerator(
                    experiment=self.experiment,
                    prog_name=self.name,
                    verbosity=self.verbosity)

    def apply(self, args):
        '''
        Initialize an instance of the API class corresponding to the program
        and process arguments of the "apply" subparser.

        Parameters
        ----------
        args: tmlib.args.ApplyArgs
            method-specific arguments
        '''
        self._print_logo()
        api = self._api_instance
        logger.info('apply statistics')
        api.apply_statistics(
                output_dir=args.output_dir,
                plates=args.plates,
                wells=args.wells,
                sites=args.sites,
                channels=args.channels,
                tpoints=args.tpoints,
                zplanes=args.zplanes,
                **dict(args.variable_args))

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
        :py:mod:`tmlib.corilla.argparser`
        '''
        experiment = Experiment(args.experiment_dir)
        cli = Corilla(experiment, args.verbosity)
        cli._call(args)
