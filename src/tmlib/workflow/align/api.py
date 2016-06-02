import logging
from collections import defaultdict

import tmlib.models as tm
from tmlib.image_utils import mip
from tmlib.utils import notimplemented
from tmlib.utils import same_docstring_as
from tmlib.errors import NotSupportedError
from tmlib.workflow.align import registration as reg
from tmlib.workflow.api import ClusterRoutines
from tmlib.workflow.registry import api

logger = logging.getLogger(__name__)


@api('align')
class ImageRegistrator(ClusterRoutines):

    '''Class for registering and aligning images between cycles.
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

        with tm.utils.Session() as session:

            for plate in session.query(tm.Plate).\
                    filter_by(experiment_id=self.experiment_id):

                if not(len(plate.cycles) > 1):
                    raise NotSupportedError(
                        'Alignment requires more than one cycle.'
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

                        for s in batch:

                            files = session.query(
                                    tm.ChannelImageFile
                                ).\
                                join(tm.Site).\
                                join(tm.Cycle).\
                                join(tm.Channel).\
                                filter(tm.Site.id == s).\
                                filter(tm.Cycle.id == cycle.id).\
                                filter(tm.Channel.wavelength == args.ref_wavelength).\
                                filter(~tm.ChannelImageFile.omitted).\
                                all()

                            if not files:
                                logger.warning(
                                    'no files for site %d and cycle %d',
                                    s, cycle.id
                                )
                                continue

                            ids = [f.id for f in files]
                            if cycle.index == args.ref_cycle:
                                input_ids['reference_file_ids'].append(ids)
                            input_ids['target_file_ids'][cycle.id].append(ids)

                    job_descriptions['run'].append({
                        'id': job_count,
                        'input_ids': input_ids,
                        'inputs': dict(),
                        'outputs': dict(),
                    })

        return job_descriptions

    @same_docstring_as(ClusterRoutines.delete_previous_job_output)
    def delete_previous_job_output(self):
        with tm.utils.Session() as session:

            cycle_ids = session.query(tm.Cycle.id).\
                join(tm.Plate).\
                filter(tm.Plate.experiment_id == self.experiment_id).\
                all()
            cycle_ids = [p[0] for p in cycle_ids]

            site_ids = session.query(tm.Site.id).\
                join(tm.Well).\
                join(tm.Plate).\
                filter(tm.Plate.experiment_id == self.experiment_id).\
                all()
            site_ids = [p[0] for p in site_ids]

        if cycle_ids:

            with tm.utils.Session() as session:

                logger.info('delete existing site shifts')
                session.query(tm.SiteShift).\
                    filter(tm.SiteShift.cycle_id.in_(cycle_ids)).\
                    delete()

        if site_ids:

            with tm.utils.Session() as session:

                logger.info('delete existing site intersections')
                session.query(tm.SiteIntersection).\
                    filter(tm.SiteIntersection.site_id.in_(site_ids)).\
                    delete()

    def run_job(self, batch):
        '''Calculate shift and overhang values for the given sites.

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
        for i, reference_ids in enumerate(reference_file_ids):
            with tm.utils.Session() as session:
                reference_files = [
                    session.query(tm.ChannelImageFile).get(rid)
                    for rid in reference_ids
                ]
                ref_img = mip([f.get().pixels for f in reference_files])
                logger.info(
                    'register images at site %d', reference_files[0].site_id
                )
                y_shifts = list()
                x_shifts = list()
                for target_ids in target_file_ids.values():
                    target_files = [
                        session.query(tm.ChannelImageFile).get(tid)
                        for tid in target_ids[i]
                    ]
                    logger.info(
                        'calculate shifts for cycle %d',
                        target_files[0].cycle_id
                    )
                    target_img = mip([f.get().pixels for f in target_files])
                    y, x = reg.calculate_shift(target_img, ref_img)

                    session.get_or_create(
                        tm.SiteShift,
                        x=x, y=y,
                        site_id=target_files[0].site_id,
                        cycle_id=target_files[0].cycle_id
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
                    site_id=reference_files[0].site_id
                )

    @notimplemented
    def collect_job_output(self, batch):
        pass
        # TODO: set shifts to zero for sites that were omitted

