import logging
from . import logo
from . import __version__
from .api import ImageAnalysisPipeline
from ..cli import CommandLineInterface
from ..experiment import Experiment

logger = logging.getLogger(__name__)


class Jterator(CommandLineInterface):

    def __init__(self, args):
        '''
        Initialize an instance of class Jterator.

        Parameters
        ----------
        args: argparse.Namespace
            parsed command line arguments

        Returns
        -------
        tmlib.jterator.cli.Jterator
        '''
        super(Jterator, self).__init__(args)
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
            name of the command line program
        '''
        return self.__class__.__name__.lower()

    @property
    def _api_instance(self):
        experiment = Experiment(self.args.experiment_dir)
        return ImageAnalysisPipeline(
                                experiment=experiment, prog_name=self.name,
                                verbosity=self.args.verbosity,
                                pipe_name=self.args.pipeline,
                                headless=self.args.headless)

    def create(self):
        '''
        Initialize an instance of the API class corresponding to the specific
        command line interface and process arguments of the "create" subparser.
        '''
        self.print_logo()
        api = self._api_instance
        logger.info('create project: %s' % api.project_dir)
        api.project.create(self.args.repo_dir, self.args.skel_dir)

    def remove(self):
        '''
        Initialize an instance of the API class corresponding to the specific
        command line interface and process arguments of the "remove" subparser.
        '''
        self.print_logo()
        api = self._api_instance
        logger.info('remove project: %s' % api.project_dir)
        api.project.remove()

    def check(self):
        '''
        Initialize an instance of the API class corresponding to the specific
        command line interface and process arguments of the "check" subparser.
        '''
        self.print_logo()
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
        `tmlib.jterator.argparser`_
        '''
        cli = Jterator(args)
        logger.debug('call "%s" method of class "%s"'
                     % (args.method_name, cli.__class__.__name__))
        getattr(cli, args.method_name)()
