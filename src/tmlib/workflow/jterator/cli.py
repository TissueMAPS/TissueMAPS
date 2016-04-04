import logging

from tmlib.utils import same_docstring_as
from tmlib.workflow.jterator import logo
from tmlib.workflow.jterator.api import ImageAnalysisPipeline
from tmlib.workflow.cli import CommandLineInterface

logger = logging.getLogger(__name__)


class Jterator(CommandLineInterface):

    '''Command line interface for image analysis pipelines.'''

    def __init__(self, api_instance, verbosity):
        '''
        Parameters
        ----------
        api_instance: tmlib.workflow.jterator.ImageAnalysisPipeline
            instance of API class to which processing is delegated
        verbosity: int
            logging level
        '''
        super(Jterator, self).__init__(api_instance, verbosity)

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
        logger.info('create project: %s' % api.step_location)
        api.project.create(
            args.variable_args.repo_dir, args.variable_args.skel_dir
        )

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
        logger.info('remove project: %s' % api.step_location)
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
    def _print_logo():
        print logo

    @staticmethod
    @same_docstring_as(CommandLineInterface.call)
    def call(name, args):
        api_instance = ImageAnalysisPipeline(
            args.experiment_id, args.verbosity, args.pipeline
        )
        Jterator(api_instance, args.verbosity)._call(args)
