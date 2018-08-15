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
from collections import defaultdict

import tmlib.models as tm
from tmlib.utils import notimplemented
from tmlib.utils import same_docstring_as
from tmlib.errors import NotSupportedError
from sqlalchemy.orm.exc import NoResultFound
from tmlib.errors import JobDescriptionError
from tmlib.workflow.align import registration as reg
from tmlib.workflow.api import WorkflowStepAPI
from tmlib.workflow import register_step_api

logger = logging.getLogger(__name__)


@register_step_api('align')
class ImageRegistrator(WorkflowStepAPI):

    '''Class for registeration and alignment of images between multiplexing
    cycles.
    '''

    def __init__(self, experiment_id):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of the processed experiment
        '''
        super(ImageRegistrator, self).__init__(experiment_id)

    def create_run_batches(self, args):
        '''Creates job descriptions for parallel computing.

        Parameters
        ----------
        args: tmlib.workflow.align.args.AlignBatchArguments
            step-specific arguments

        Returns
        -------
        generator
            job descriptions

        Raises
        ------
        ValueError
            when `args.ref_wavelength` does not exist across all cycles
        '''
        job_count = 0

        with tm.utils.ExperimentSession(self.experiment_id) as session:

            cycles = session.query(tm.Cycle).all()

            if not(len(cycles) > 1):
                raise NotSupportedError(
                    'Alignment requires more than one cycle.'
                )

            if args.ref_cycle >= len(cycles):
                raise JobDescriptionError(
                    'Cycle index must not exceed total number of cycles.'
                )

            site_ids = session.query(tm.Site.id).\
                order_by(tm.Site.id).\
                all()

            batches = self._create_batches(site_ids, args.batch_size)
            for batch in batches:

                job_count += 1
                input_ids = {
                    'reference_file_ids': list(),
                    'target_file_ids': defaultdict(list)
                }

                for cycle in cycles:

                    n = session.query(tm.ChannelImageFile.id).\
                        join(tm.Cycle).\
                        join(tm.Channel).\
                        filter(tm.Cycle.id == cycle.id).\
                        filter(tm.Channel.wavelength == args.ref_wavelength).\
                        filter(~tm.Site.omitted).\
                        count()

                    if n == 0:
                        raise ValueError(
                            'No image files found for cycle %d and '
                            'wavelength "%s"'
                            % (cycle.id, args.ref_wavelength)
                        )

                    for s in batch:

                        files = session.query(tm.ChannelImageFile.id).\
                            join(tm.Site).\
                            join(tm.Cycle).\
                            join(tm.Channel).\
                            filter(tm.Site.id == s).\
                            filter(tm.Cycle.id == cycle.id).\
                            filter(tm.Channel.wavelength == args.ref_wavelength).\
                            filter(~tm.Site.omitted).\
                            all()

                        if not files:
                            # We don't raise an Execption here, because
                            # there may be situations were an aquisition
                            # failed at a given site in one cycle, but
                            # is present in the other cycles.
                            logger.warning(
                                'no files for site %d and cycle %d',
                                s, cycle.id
                            )
                            continue

                        ids = [f.id for f in files]
                        if cycle.index == args.ref_cycle:
                            input_ids['reference_file_ids'].extend(ids)
                        input_ids['target_file_ids'][cycle.id].extend(ids)

                yield {
                    'id': job_count,
                    'input_ids': input_ids,
                    'illumcorr': args.illumcorr,
                    'robust_align': args.robust_align,
                    'rescale_percentile': args.rescale_percentile
                }

    @same_docstring_as(WorkflowStepAPI.delete_previous_job_output)
    def delete_previous_job_output(self):
        logger.info('delete existing site shifts and intersections')
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            session.query(tm.SiteShift).delete()
            for site in session.query(tm.Site).all():
                site.bottom_residue = 0
                site.top_residue = 0
                site.left_residue = 0
                site.right_residue = 0

    def run_job(self, batch, assume_clean_state=False):
        '''Calculates the number of pixels each image is shifted relative
        its reference image. The calculated values can later be used to align
        images between cycles.

        Parameters
        ----------
        batch: dict
            description of the *run* job
        assume_clean_state: bool, optional
            assume that output of previous runs has already been cleaned up

        Note
        ----
        If sites contain multiple z-planes, z-stacks are projected to 2D and
        the resulting projections are registered.
        '''
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            reference_file_ids = batch['input_ids']['reference_file_ids']
            target_file_ids = batch['input_ids']['target_file_ids']
            if batch['illumcorr'] or batch['robust_align']:
                logger.info('correct images for illumination artifacts')

                rid = reference_file_ids[0]
                reference_file = session.query(tm.ChannelImageFile).get(rid)
                try:
                    logger.debug(
                        'load illumination statistics for channel %d of '
                        'reference cycle %d', reference_file.channel_id,
                        reference_file.cycle_id
                    )
                    illumstats_file = session.query(tm.IllumstatsFile).\
                        filter_by(channel_id=reference_file.channel_id).\
                        one()
                except NoResultFound:
                    raise WorkflowError(
                        'No illumination statistics file found for channel %d'
                        % reference_file.channel_id
                    )
                reference_stats = illumstats_file.get()

                target_stats = dict()
                for cycle_id, tids in target_file_ids.iteritems():
                    target_file = session.query(tm.ChannelImageFile).get(tids[0])
                    try:
                        logger.debug(
                            'load illumination statistics for channel %d of'
                            'target cycle %d', target_file.channel_id,
                            target_file.cycle_id
                        )
                        illumstats_file = session.query(tm.IllumstatsFile).\
                            filter_by(channel_id=target_file.channel_id).\
                            one()
                    except NoResultFound:
                        raise WorkflowError(
                            'No illumination statistics file found for '
                            'channel %d'
                            % target_file.channel_id
                        )
                    target_stats[cycle_id] = illumstats_file.get()

            

            for i, rid in enumerate(reference_file_ids):
                reference_file = session.query(tm.ChannelImageFile).get(rid)
                logger.info('register images at site %d', reference_file.site_id)
                logger.debug('load reference image %d', rid)
                reference_img = reference_file.get()
                if batch['illumcorr']:
                    logger.debug('correct reference image')
                    reference_img = reference_img.correct(reference_stats)
                
                if batch['robust_align']:
                    logger.debug('clip image for robust alignment')
                    clip_max = reference_stats.get_closest_percentile(
                                batch['rescale_percentile']
                            )
                    logger.info('clip value: %d', clip_max)
                    clip_min = 0
                    reference_img = reference_img.clip(clip_min, clip_max)

                y_shifts = list()
                x_shifts = list()
                for cycle_id, tids in target_file_ids.iteritems():
                    logger.info('calculate shifts for cycle %s', cycle_id)
                    logger.debug('load target image %d', tids[i])
                    target_file = session.query(tm.ChannelImageFile).get(tids[i])
                    target_img = target_file.get()
                    if batch['illumcorr']:
                        logger.debug('correct target image')
                        target_img = target_img.correct(target_stats[cycle_id])

                    if batch['robust_align']:
                        logger.debug('clip image for robust alignment')
                        clip_max = target_stats[cycle_id].get_closest_percentile(
                                    batch['rescale_percentile']
                                )
                        logger.info('clip value: %d', clip_max)
                        clip_min = 0
                        target_img = target_img.clip(clip_min, clip_max)

                    y, x = reg.calculate_shift(
                        target_img.array, reference_img.array
                    )

                    session.get_or_create(
                        tm.SiteShift,
                        x=x, y=y,
                        site_id=target_file.site_id,
                        cycle_id=target_file.cycle_id
                    )

                    y_shifts.append(y)
                    x_shifts.append(x)

                logger.info('calculate intersection of sites across cycles')
                bottom, top, left, right = reg.calculate_overlap(
                    y_shifts, x_shifts
                )

                site = session.query(tm.Site).get(reference_file.site_id)
                site.bottom_residue = bottom
                site.top_residue = top
                site.left_residue = left
                site.right_residue = right

    @notimplemented
    def collect_job_output(self, batch):
        pass
        # TODO: set shifts to zero for sites that were omitted

