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
import os
import logging
from sqlalchemy import func

import tmlib.models as tm
from tmlib.utils import notimplemented
from tmlib.image import IllumstatsContainer
from tmlib.models.utils import delete_location
from tmlib.workflow.api import WorkflowStepAPI
from tmlib.workflow.corilla.stats import OnlineStatistics
from tmlib.workflow import register_step_api

logger = logging.getLogger(__name__)


@register_step_api('corilla')
class IllumstatsCalculator(WorkflowStepAPI):

    '''Class for calculating illumination statistics.'''

    def __init__(self, experiment_id):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of parent experiment
        '''
        super(IllumstatsCalculator, self).__init__(experiment_id)

    def create_run_batches(self, args):
        '''Creates job descriptions for parallel computing.

        Parameters
        ----------
        args: tmlib.workflow.corilla.args.CorillaBatchArguments
            step-specific arguments

        Returns
        -------
        generator
            job descriptions
        '''
        count = 0

        with tm.utils.ExperimentSession(self.experiment_id) as session:
            # NOTE: Illumination statistics are calculated for each channel
            # over all plates and time pionts, assuming that imaging conditions
            # are consistent within an experiment.
            channels = session.query(tm.Channel.id, tm.Channel.name).all()
            for ch in channels:
                # We only use a subset of images in case there are tens or
                # hundreds of thousands of them. Twenty thousand should be more
                # than enough for robust illumination statistics.
                limit = 20000
                n = session.query(tm.ChannelImageFile.id).\
                    filter_by(channel_id=ch.id).\
                    count()
                if n > limit:
                    logger.info(
                        'using a subset of image files (n=%d) to calculate '
                        'illumination statistics for channel "%s"', limit,
                        ch.name
                    )
                    file_ids = session.query(tm.ChannelImageFile.id).\
                        filter_by(channel_id=ch.id).\
                        order_by(func.random()).\
                        limit(limit).\
                        all()
                else:
                    if n < 100:
                        logger.warn(
                            'calculation of illumnation statistics for channel '
                            '"%s" on only %d images - this may introduce '
                            'artifacts upon illumination correction', ch.name, n
                        )
                    file_ids = session.query(tm.ChannelImageFile.id).\
                        filter_by(channel_id=ch.id).\
                        all()
                if not file_ids:
                    logger.warning(
                        'no image files found for channel "%s"', ch.name
                    )
                    continue

                count += 1
                yield {
                    'id': count,
                    'channel_image_files_ids': file_ids,
                    'channel_id': ch.id,
                }

    def delete_previous_job_output(self):
        '''Deletes all :class:`tmlib.models.file.IllumstatsFile` instances
        of the processed experiment.
        '''
        logger.info('delete existing illumination statistics files')
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            session.query(tm.IllumstatsFile).delete()

    def run_job(self, batch, assume_clean_state=False):
        '''Calculates illumination statistics.

        Parameters
        ----------
        batch: dict
            job description
        assume_clean_state: bool, optional
            assume that output of previous runs has already been cleaned up
        '''
        file_ids = batch['channel_image_files_ids']
        logger.info('calculate illumination statistics')
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            img_file = session.query(tm.ChannelImageFile).get(file_ids[0])
            img = img_file.get()
        stats = OnlineStatistics(image_dimensions=img.dimensions[0:2])
        for fid in file_ids:
            with tm.utils.ExperimentSession(self.experiment_id) as session:
                img_file = session.query(tm.ChannelImageFile).get(fid)
                logger.info('update statistics for image: %d', img_file.id)
                img = img_file.get()
                stats.update(img)

        with tm.utils.ExperimentSession(self.experiment_id) as session:
            stats_file = session.get_or_create(
                tm.IllumstatsFile, channel_id=batch['channel_id']
            )
            logger.info('write calculated statistics to file')
            illumstats = IllumstatsContainer(
                stats.mean, stats.std, stats.percentiles
            )
            stats_file.put(illumstats)

    @notimplemented
    def collect_job_output(self, batch):
        pass

