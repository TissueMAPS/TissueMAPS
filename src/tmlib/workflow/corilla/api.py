import os
import logging

import tmlib.models as tm
from tmlib.utils import notimplemented
from tmlib.image import IllumstatsContainer
from tmlib.workflow.api import ClusterRoutines
from tmlib.workflow.corilla.stats import OnlineStatistics
from tmlib.workflow import register_api

logger = logging.getLogger(__name__)


@register_api('corilla')
class IllumstatsCalculator(ClusterRoutines):

    '''Class for calculating illumination statistics.'''

    def __init__(self, experiment_id, verbosity):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of parent experiment
        verbosity: int
            logging level
        '''
        super(IllumstatsCalculator, self).__init__(experiment_id, verbosity)

    def create_batches(self, args):
        '''Creates job descriptions for parallel computing.

        Parameters
        ----------
        args: tmlib.corilla.args.CorillaInitArgs
            step-specific arguments

        Returns
        -------
        Dict[str, List[dict] or dict]
            job descriptions
        '''
        job_descriptions = dict()
        job_descriptions['run'] = list()
        count = 0

        with tm.utils.Session() as session:

            channels = session.query(tm.Channel).\
                filter_by(experiment_id=self.experiment_id).\
                all()

            # NOTE: Illumination statistics are calculated for each cycle
            # separately. This should be safer, since imaging condition might
            # differ between cycles. 

            # TODO: Enable pooling image files across cycles, which may be
            # necessary to get enough images for robust statistics in case
            # each cycle has only a few images.
            for cycle in session.query(tm.Cycle).\
                    join(tm.Plate).\
                    join(tm.Experiment).\
                    filter(tm.Experiment.id == self.experiment_id):

                for channel in channels:

                    files = [
                        f for f in cycle.channel_image_files
                        if f.channel_id == channel.id
                    ]

                    if not files:
                        continue

                    count += 1
                    job_descriptions['run'].append({
                        'id': count,
                        'inputs': {
                            'channel_image_files': [
                                f.location for f in files
                            ]
                        },
                        'outputs': {
                            'illumstats_files': [
                                os.path.join(
                                    cycle.illumstats_location,
                                    tm.IllumstatsFile.
                                    FILENAME_FORMAT.format(
                                        channel_id=channel.id
                                    )
                                )
                            ]
                        },
                        'channel_image_files_ids': [
                            f.id for f in files
                        ],
                        'channel_id': channel.id,
                        'cycle_id': cycle.id
                    })
        return job_descriptions

    def delete_previous_job_output(self):
        '''Deletes all instances of class
        :py:class:`tm.IllumstatsFile` as well as all children for the
        processed experiment.
        '''
        with tm.utils.Session() as session:

            cycle_ids = session.query(tm.Cycle.id).\
                join(tm.Plate).\
                filter(tm.Plate.experiment_id == self.experiment_id).\
                all()
            cycle_ids = [p[0] for p in cycle_ids]

        if cycle_ids:

            with tm.utils.Session() as session:

                logger.info('delete existing illumination statistics files')
                session.query(tm.IllumstatsFile).\
                    filter(tm.IllumstatsFile.cycle_id.in_(cycle_ids)).\
                    delete()

    def run_job(self, batch):
        '''Calculates illumination statistics.

        Parameters
        ----------
        batch: dict
            job description
        '''
        file_ids = batch['channel_image_files_ids']
        logger.info('calculate illumination statistics')
        with tm.utils.Session() as session:
            file = session.query(tm.ChannelImageFile).get(file_ids[0])
            img = file.get(z=0)
        stats = OnlineStatistics(image_dimensions=img.dimensions[0:2])
        for fid in file_ids:
            with tm.utils.Session() as session:
                file = session.query(tm.ChannelImageFile).get(fid)
                logger.info('update statistics for image: %s', file.name)
                for z in xrange(file.n_planes):
                    img = file.get(z=z)
                    stats.update(img)

        with tm.utils.Session() as session:
            stats_file = session.get_or_create(
                tm.IllumstatsFile,
                channel_id=batch['channel_id'], cycle_id=batch['cycle_id']
            )
            logger.info('write calculated statistics to file')
            illumstats = IllumstatsContainer(
                stats.mean, stats.std, stats.percentiles
            )
            stats_file.put(illumstats)

    @notimplemented
    def collect_job_output(self, batch):
        pass

