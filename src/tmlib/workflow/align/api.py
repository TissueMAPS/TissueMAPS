import logging
from collections import defaultdict

import tmlib.models
from tmlib.image_utils import mip
from tmlib.utils import notimplemented
from tmlib.errors import NotSupportedError
from tmlib.workflow.align import registration as reg
from tmlib.workflow.api import ClusterRoutines

logger = logging.getLogger(__name__)


class ImageRegistration(ClusterRoutines):

    '''Class for registering and aligning images between cycles.
    '''

    def __init__(self, experiment_id, step_name, verbosity, **kwargs):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of the processed experiment
        step_name: str
            name of the corresponding program (command line interface)
        verbosity: int
            logging level
        **kwargs: dict, optional
            ignored keyword arguments
        '''
        super(ImageRegistration, self).__init__(
            experiment_id, step_name, verbosity
        )

    def create_batches(self, args):
        '''Create job descriptions for parallel computing.

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

        # TODO: group z-planes

        with tmlib.models.utils.Session() as session:

            for plate in session.query(tmlib.models.Plate).\
                    filter_by(experiment_id=self.experiment_id):

                if not(len(plate.cycles) > 1):
                    raise NotSupportedError(
                        'Alignment requires more than one cycle.'
                    )

                sites = session.query(tmlib.models.Site).\
                    join(tmlib.models.Well).\
                    join(tmlib.models.Plate).\
                    filter(tmlib.models.Plate.id == plate.id).\
                    all()

                site_ids = [s.id for s in sites]
                batches = self._create_batches(site_ids, args.batch_size)
                for batch in batches:

                    job_count += 1
                    input_ids = {
                        'reference_file_ids': list(),
                        'target_file_ids': defaultdict(list)
                    }

                    for cycle in plate.cycles:

                        for s in batch:

                            files = session.query(tmlib.models.ChannelImageFile).\
                                filter_by(
                                    site_id=s,
                                    cycle_id=cycle.id,
                                    wavelength=args.ref_wavelength
                                ).\
                                all()

                            if not files:
                                raise ValueError(
                                    'No channel image files found for site %d '
                                    'and cycle %d.' % (s, cycle.id)
                                )

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
            with tmlib.models.utils.Session() as session:
                reference_files = [
                    session.query(tmlib.models.ChannelImageFile).get(rid)
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
                        session.query(tmlib.models.ChannelImageFile).get(tid)
                        for tid in target_ids[i]
                    ]
                    logger.info(
                        'calculate shifts for cycle %d',
                        target_files[0].cycle_id
                    )
                    target_img = mip([f.get().pixels for f in target_files])
                    y, x = reg.calculate_shift(target_img, ref_img)

                    session.get_or_create(
                        tmlib.models.SiteShift,
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
                    tmlib.models.SiteIntersection,
                    upper_overhang=top, lower_overhang=bottom,
                    right_overhang=right, left_overhang=left,
                    site_id=reference_files[0].site_id
                )

    @notimplemented
    def collect_job_output(self, batch):
        pass
