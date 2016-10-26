import logging
from collections import defaultdict

import tmlib.models as tm
from tmlib.utils import notimplemented
from tmlib.utils import same_docstring_as
from tmlib.errors import NotSupportedError
from tmlib.errors import JobDescriptionError
from tmlib.workflow.align import registration as reg
from tmlib.workflow.api import ClusterRoutines
from tmlib.workflow import register_api

logger = logging.getLogger(__name__)


@register_api('align')
class ImageRegistrator(ClusterRoutines):

    '''Class for registeration and alignment of images between multiplexing
    cycles.
    '''

    def __init__(self, experiment_id, verbosity):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of the processed experiment
        verbosity: int
            logging level
        '''
        super(ImageRegistrator, self).__init__(experiment_id, verbosity)

    def create_batches(self, args):
        '''Creates job descriptions for parallel computing.

        Parameters
        ----------
        args: tmlib.align.args.AlignInitArgs
            step-specific arguments

        Returns
        -------
        Dict[str, List[dict] or dict]
            job descriptions

        Raises
        ------
        tmlib.errors.NotSupportedError
            when a plate contains only one cycle
        ValueError
            when `args.ref_wavelength` does not exist across all cycles
        '''
        job_count = 0
        job_descriptions = dict()
        job_descriptions['run'] = list()

        with tm.utils.ExperimentSession(self.experiment_id) as session:

            for plate in session.query(tm.Plate):

                if not(len(plate.cycles) > 1):
                    raise NotSupportedError(
                        'Alignment requires more than one cycle.'
                    )

                if args.ref_cycle >= len(plate.cycles):
                    raise JobDescriptionError(
                        'Cycle index must not exceed total number of cycles.'
                    )

                site_ids = session.query(tm.Site.id).\
                    join(tm.Well).\
                    join(tm.Plate).\
                    filter(tm.Plate.id == plate.id).\
                    order_by(tm.Site.id).\
                    all()

                batches = self._create_batches(site_ids, args.batch_size)
                for batch in batches:

                    job_count += 1
                    input_ids = {
                        'reference_file_ids': list(),
                        'target_file_ids': defaultdict(list)
                    }

                    for cycle in plate.cycles:

                        n = session.query(tm.ChannelImageFile.id).\
                            join(tm.Cycle).\
                            join(tm.Channel).\
                            filter(tm.Cycle.id == cycle.id).\
                            filter(tm.Channel.wavelength == args.ref_wavelength).\
                            filter(~tm.ChannelImageFile.omitted).\
                            count()

                        if n == 0:
                            raise ValueError(
                                'No image files found for cycle %d and '
                                'wavelength "%s"'
                                % (cycle.id, args.ref_wavelength)
                            )

                        for s in batch:

                            files = session.query(tm.ChannelImageFile).\
                                join(tm.Site).\
                                join(tm.Cycle).\
                                join(tm.Channel).\
                                filter(tm.Site.id == s).\
                                filter(tm.Cycle.id == cycle.id).\
                                filter(tm.Channel.wavelength == args.ref_wavelength).\
                                filter(~tm.ChannelImageFile.omitted).\
                                all()

                            if not files:
                                # We don't raise an Execption here, because
                                # there may be situations were an aquisition
                                # failed at a given site in one cycle, but was
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

                    job_descriptions['run'].append({
                        'id': job_count,
                        'input_ids': input_ids,
                        'inputs': dict(),
                        'outputs': dict(),
                    })

        return job_descriptions

    @same_docstring_as(ClusterRoutines.delete_previous_job_output)
    def delete_previous_job_output(self):
        logger.info('delete existing site shifts and intersections')
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            session.drop_and_recreate(tm.SiteShift)
            session.drop_and_recreate(tm.SiteIntersection)

    def run_job(self, batch):
        '''Calculates shift and overhang values for the given sites.

        Parameters
        ----------
        batch: dict
            description of the *run* job

        Note
        ----
        If sites contain multiple z-planes, z-stacks are projected to 2D and
        the resulting projections are registered.
        '''
        reference_file_ids = batch['input_ids']['reference_file_ids']
        target_file_ids = batch['input_ids']['target_file_ids']
        for i, rid in enumerate(reference_file_ids):
            with tm.utils.ExperimentSession(self.experiment_id) as session:
                reference_file = session.query(tm.ChannelImageFile).get(rid)
                reference_img = reference_file.get().project().array
                logger.info(
                    'register images at site %d', reference_file.site_id
                )
                y_shifts = list()
                x_shifts = list()
                for tids in target_file_ids.values():
                    target_file = session.query(tm.ChannelImageFile).get(tids[i])
                    logger.info(
                        'calculate shifts for cycle %d', target_file.cycle_id
                    )
                    target_img = target_file.get().project().array
                    y, x = reg.calculate_shift(target_img, reference_img)

                    session.get_or_create(
                        tm.SiteShift,
                        x=x, y=y,
                        site_id=target_file.site_id,
                        cycle_id=target_file.cycle_id
                    )

                    y_shifts.append(y)
                    x_shifts.append(x)

                logger.info('calculate intersection of sites across cycles')
                top, bottom, right, left = reg.calculate_overhang(
                    y_shifts, x_shifts
                )

                session.get_or_create(
                    tm.SiteIntersection,
                    upper_overhang=top, lower_overhang=bottom,
                    right_overhang=right, left_overhang=left,
                    site_id=reference_file.site_id
                )

    @notimplemented
    def collect_job_output(self, batch):
        pass
        # TODO: set shifts to zero for sites that were omitted

