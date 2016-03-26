import os
import logging

import tmlib.models
from tmlib.utils import notimplemented
from tmlib.writers import DatasetWriter
from tmlib.workflow.api import ClusterRoutines
from tmlib.workflow.corilla.stats import OnlineStatistics
from tmlib.workflow.corilla.stats import OnlinePercentile

logger = logging.getLogger(__name__)


class IllumstatsGenerator(ClusterRoutines):

    '''Class for calculating illumination statistics.'''

    def __init__(self, experiment_id, step_name, verbosity, **kwargs):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of parent experiment
        step_name: str
            name of the corresponding program (command line interface)
        verbosity: int
            logging level
        **kwargs: dict
            ignored keyword arguments
        '''
        super(IllumstatsGenerator, self).__init__(
            experiment_id, step_name, verbosity
        )

    def create_batches(self, args):
        '''
        Create job descriptions for parallel computing.

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

        with tmlib.models.utils.Session() as session:

            channels = session.query(tmlib.models.Channel).\
                filter_by(experiment_id=self.experiment_id).\
                all()

            # NOTE: Illumination statistics are calculated for each cycle
            # separately. This should be safer, since imaging condition might
            # differ between cycles. 

            # TODO: Enable pooling image files across cycles, which may be
            # necessary to get enough images for robust statistics in case
            # each cycle has only a few images.
            for cycle in session.query(tmlib.models.Cycle).\
                    join(tmlib.models.Plate).\
                    join(tmlib.models.Experiment).\
                    filter(tmlib.models.Experiment.id == self.experiment_id):

                for channel in channels:

                    files = [
                        f for f in cycle.channel_image_files
                        if f.channel_layer.channel.id == channel.id
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
                                    tmlib.models.IllumStatsFile.
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

    def run_job(self, batch):
        '''
        Calculate online statistics and write results to a HDF5 file.

        Parameters
        ----------
        batch: dict
            job_descriptions element
        '''
        file_ids = batch['channel_image_files_ids']
        logger.info('calculate illumination statistics')
        with tmlib.models.utils.Session() as session:
            file = session.query(tmlib.models.ChannelImageFile).get(file_ids[0])
            img = file.get()
        stats = OnlineStatistics(image_dimensions=img.dimensions)
        pctl = OnlinePercentile()
        for fid in file_ids:
            with tmlib.models.utils.Session() as session:
                file = session.query(tmlib.models.ChannelImageFile).get(fid)
                img = file.get()
                logger.info('update statistics for image: %s', file.name)
            stats.update(img.pixels)
            pctl.update(img.pixels)

        with tmlib.models.utils.Session() as session:
            stats_file = session.get_or_create(
                tmlib.models.IllumStatsFile,
                channel_id=batch['channel_id'], cycle_id=batch['cycle_id']
            )
            logger.info('write calculated statistics to file')
            with DatasetWriter(stats_file.location, truncate=True) as writer:
                writer.write('/mean', data=stats.mean)
                writer.write('/std', data=stats.std)
                writer.write(
                    '/percentiles/values', data=pctl.percentiles.values()
                )
                writer.write(
                    '/percentiles/keys', data=pctl.percentiles.keys()
                )

    @notimplemented
    def collect_job_output(self, batch):
        pass
