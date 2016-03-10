import logging
from . import logo
from . import __version__
from .api import ImageAnalysisPipeline
from ..cli import CommandLineInterface
from ..experiment import Experiment

logger = logging.getLogger(__name__)


class Jterator(CommandLineInterface):

    def __init__(self, experiment, verbosity, pipeline, **kwargs):
        '''
        Initialize an instance of class Jterator.

        Parameters
        ----------
        experiment: tmlib.experiment.Experiment
            configured experiment object
        verbosity: int
            logging level
        pipeline: str
            name of the pipeline that should be processed
        kwargs: dict
            additional key-value pairs that are ignored
        '''
        super(Jterator, self).__init__(experiment, verbosity)
        self.pipeline = pipeline

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
        return ImageAnalysisPipeline(
                    self.experiment, self.name, self.verbosity,
                    self.pipeline)

    def create(self, args):
        '''
        Initialize an instance of the API class corresponding to the specific
        command line interface and process arguments of the "create" subparser.

        Parameters
        ----------
        args: tmlib.args.CreateArgs
            method-specific arguments
        '''
        self._print_logo()
        api = self._api_instance
        logger.info('create project: %s' % api.project_dir)
        api.project.create(args.variable_args.repo_dir,
                           args.variable_args.skel_dir)

    def remove(self, args):
        '''
        Initialize an instance of the API class corresponding to the specific
        command line interface and process arguments of the "remove" subparser.

        Parameters
        ----------
        args: tmlib.args.RemoveArgs
            method-specific arguments
        '''
        self._print_logo()
        api = self._api_instance
        logger.info('remove project: %s' % api.project_dir)
        api.project.remove()

    def check(self, args):
        '''
        Initialize an instance of the API class corresponding to the specific
        command line interface and process arguments of the "check" subparser.

        Parameters
        ----------
        args: tmlib.args.CheckArgs
            method-specific arguments
        '''
        self._print_logo()
        api = self._api_instance
        logger.info('check pipe and handle descriptor files')
        api.check_pipeline()

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
        :py:mod:`tmlib.jterator.argparser`
        '''
        experiment = Experiment(args.experiment_dir, library='numpy')
        # We reverse the logic for "headless" mode, because the default for
        # command line use is not to plot.
        Jterator(experiment, args.verbosity, args.pipeline)._call(args)
