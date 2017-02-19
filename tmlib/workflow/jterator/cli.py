# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
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
        help='runs an invidiual job on the local machine',
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
            logger.info('get batch for job #%d', job_id)
            batch = api.get_run_batch(job_id)
            logger.info('run job #%d' % job_id)
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

