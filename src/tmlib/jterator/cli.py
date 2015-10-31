import logging
from . import logo
from . import __version__
from .api import ImageAnalysisPipeline
from ..cli import CommandLineInterface

logger = logging.getLogger(__name__)


class Jterator(CommandLineInterface):

    def __init__(self, experiment_dir, verbosity, pipeline_name, headless):
        '''
        Initialize an instance of class Jterator.

        Parameters
        ----------
        experiment_dir: str
            path to the experiment directory
        verbosity: int
            logging level
        pipeline_name: str
            name of the processed pipeline
        headless: bool
            indicator that program should run in headless mode,
            i.e. that modules should not generate any plots

        Raises
        ------
        TypeError
            when `pipeline_name` doesn't have type str and/or when
            `headless` doesn't have type bool
        '''
        super(Jterator, self).__init__(experiment_dir, verbosity)
        self.experiment_dir = experiment_dir
        self.verbosity = verbosity
        if not isinstance(pipeline_name, basestring):
            raise TypeError('Argument "pipeline_name" must have type str.')
        self.pipeline_name = str(pipeline_name)
        if not isinstance(headless, bool):
            raise TypeError('Argument "headless" must have type bool.')
        self.headless = headless

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
                    experiment=self.experiment,
                    prog_name=self.name,
                    verbosity=self.verbosity,
                    pipe_name=self.pipeline,
                    headless=self.headless)

    def create(self, create_args):
        '''
        Initialize an instance of the API class corresponding to the specific
        command line interface and process arguments of the "create" subparser.

        Parameters
        ----------
        create_args: tmlib.args.CreateArgs
            method-specific arguments
        '''
        self._print_logo()
        api = self._api_instance
        logger.info('create project: %s' % api.project_dir)
        api.project.create(create_args.repo_dir, create_args.skel_dir)

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
        logger.info('check pipe and handles descriptor files')
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
        cli = Jterator(args.experiment_dir, args.verbosity,
                       args.pipeline, not args.plot)
        cli._call(args)
