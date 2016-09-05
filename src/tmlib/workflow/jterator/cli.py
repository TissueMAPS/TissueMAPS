import logging

from tmlib.utils import assert_type
from tmlib.workflow.cli import CommandLineInterface
from tmlib.workflow.cli import climethod
from tmlib.workflow.args import Argument

logger = logging.getLogger(__name__)


class Jterator(CommandLineInterface):

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

    @climethod(
        help='runs an invidiual jobs on the local machine',
        job_id=Argument(
            type=int, help='ID of the job that should be run', flag='j'
        ),
        debug=Argument(
            type=bool, help='perform a debug run (only supported for 2D images)',
            flag='d', default=False
        )
    )
    def run(self, job_id, debug):
        self._print_logo()
        api = self.api_instance
        if debug:
            logger.warn('debug mode')
            batch = {'debug': True, 'plot': False}
        else:
            logger.info('read job description from batch file')
            batch_file = api.build_batch_filename_for_run_job(job_id)
            batch = api.read_batch_file(batch_file)
            logger.info('run job #%d' % batch['id'])
        api.run_job(batch)

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

