import logging
from . import logo
from . import __version__
from .api import ImageAnalysisPipeline
from ..cli import CommandLineInterface
from ..experiment import Experiment

logger = logging.getLogger(__name__)


class Jterator(CommandLineInterface):

    def __init__(self, args):
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
            name of the program
        '''
        return self.__class__.__name__.lower()

    @property
    def _api_instance(self):
        logger.debug('parsed arguments: {0}'.format(self.args))
        experiment = Experiment(self.args.experiment_dir)
        self.__api_instance = ImageAnalysisPipeline(
                                experiment=experiment, prog_name=self.name,
                                verbosity=self.args.verbosity,
                                pipe_name=self.args.pipeline)
        logger.debug(
            'instantiated API class "%s" with parsed arguments'
            % self.__api_instance.__class__.__name__)
        return self.__api_instance

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
        Calls the method that matches the name of the specified subparser with
        the parsed command line arguments.

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
