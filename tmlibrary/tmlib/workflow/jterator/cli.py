# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016-2019 University of Zurich.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import logging

from tmlib.utils import assert_type
from tmlib.log import map_logging_verbosity
from tmlib.workflow.cli import WorkflowStepCLI
from tmlib.workflow.cli import climethod
from tmlib.workflow.args import Argument
from tmlib.workflow.jterator.api import ImageAnalysisPipelineEngine

logger = logging.getLogger(__name__)


class Jterator(WorkflowStepCLI):

    @assert_type(api_instance=ImageAnalysisPipelineEngine)
    def __init__(self, api_instance, verbosity):
        '''
        Parameters
        ----------
        api_instance: tmlib.workflow.jterator.api.ImageAnalysisPipelineEngine
            instance of API class to which processing is delegated
        verbosity: int
            logging verbosity
        '''
        super(Jterator, self).__init__(api_instance, verbosity)
        self._configure_loggers()

    def _configure_loggers(self):
        # TODO: configure loggers for Python, Matlab, and R modules
        level = map_logging_verbosity(self.verbosity)
        jtlib_logger = logging.getLogger('jtlib')
        jtlib_logger.setLevel(level)
        jtmodules_logger = logging.getLogger('jtmodules')
        jtmodules_logger.setLevel(level)

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
        help='runs an invidiual job on the local machine',
        job_id=Argument(
            type=int, help='ID of the job that should be run',
            flag='job', short_flag='j'
        ),
        assume_clean_state=Argument(
            type=bool,
            help='assume that previous outputs have been cleaned up',
            flag='assume-clean-state', default=False
        )
    )
    def run(self, job_id, assume_clean_state):
        self._print_logo()
        api = self.api_instance
        logger.info('get batch for job #%d', job_id)
        batch = api.get_run_batch(job_id)
        logger.info('run job #%d' % job_id)
        api.run_job(batch, assume_clean_state)

    @climethod(
        help='runs an invidiual site on the local machine for debugging',
        site_id=Argument(
            type=int, help='ID of the site that should be run',
            flag='site', short_flag='s'
        ),
        plot=Argument(
            type=bool, help='whether figures should be generated by modules',
            default=False
        )
    )
    def debug(self, site_id, plot):
        self._print_logo()
        api = self.api_instance
        logger.info('DEBUG mode')
        logger.info('create debug batch for site %d', site_id)
        batch = {'site_ids': [site_id], 'plot': plot}
        api.run_job(batch, assume_clean_state=False)

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
