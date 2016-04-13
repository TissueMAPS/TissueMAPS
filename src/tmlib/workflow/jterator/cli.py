import logging

from tmlib.utils import assert_type
from tmlib.workflow.jterator import logo
from tmlib.workflow.cli import CommandLineInterface
from tmlib.workflow.cli import climethod
from tmlib.workflow.args import Argument

logger = logging.getLogger(__name__)


class Jterator(CommandLineInterface):

    '''Apply a sequence of algorithms to a set of images in order to
    segment the images and extract features for the identified objects.
    '''

    pipeline = Argument(
        type=str, flag='p', help='pipeline that should be processed'
    )

    @assert_type(api_instance='tmlib.workflow.jterator.api.ImageAnalysisPipeline')
    def __init__(self, api_instance):
        '''
        Parameters
        ----------
        api_instance: tmlib.workflow.jterator.api.ImageAnalysisPipeline
            instance of API class to which processing is delegated
        '''
        super(Jterator, self).__init__(api_instance)

    @climethod(
        help='creates a new project on disk',
        repo_dir=Argument(
            type=str, help='path to local copy of jtlib repository'
        ),
        skel_dir=Argument(
            type=str,
            help='path to a directory that should serve as a project skeleton'
        )
    )
    def create(self, repo_dir, skel_dir):
        self._print_logo()
        logger.info('create project: %s' % self.api_instance.step_location)
        self.api_instance.project.create(repo_dir, skel_dir)

    @climethod(help='removes an existing project')
    def remove(self):
        self._print_logo()
        logger.info('remove project: %s' % self.api_instance.step_location)
        self.api_instance.project.remove()

    @climethod(help='checks pipeline and module descriptor files')
    def check(self):
        self._print_logo()
        logger.info('check pipe and handle descriptor files')
        self.api_instance.check_pipeline()

    @staticmethod
    def _print_logo():
        print logo
