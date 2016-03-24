import os
import logging
import numpy as np
from .. import utils
from .stats import OnlineStatistics
from .stats import OnlinePercentile
from ..writers import DatasetWriter
from ..readers import ImageReader
from ..api import ClusterRoutines

logger = logging.getLogger(__name__)


class IllumstatsGenerator(ClusterRoutines):

    '''
    Class for calculating illumination statistics.
    '''

    def __init__(self, experiment, step_name, verbosity, **kwargs):
        '''
        Initialize an instance of class IllumstatsGenerator.

        Parameters
        ----------
        experiment: tmlib.experiment.Experiment
            configured experiment object
        step_name: str
            name of the corresponding program (command line interface)
        verbosity: int
            logging level
        kwargs: dict
            mapping of additional key-value pairs that are ignored
        '''
        super(IllumstatsGenerator, self).__init__(
                experiment, step_name, verbosity)

    @property
    def stats_file_format_string(self):
        '''
        Returns
        -------
        image_file_format_string: str
            format string that specifies how the names of the statistics files
            should be formatted
        '''
        return self.experiment.plates[0].cycles[0].STATS_FILE_FORMAT

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
        for plate in self.experiment.plates:
            for cycle in plate.cycles:
                md = cycle.image_metadata

                # Group image files per channel
                channels = np.unique(md.channel)
                img_batches = list()
                for c in channels:
                    files = md[(md.channel == c)].name
                    img_batches.append(files)

                for i, batch in enumerate(img_batches):
                    count += 1
                    job_descriptions['run'].append({
                        'id': count,
                        'inputs': {
                            'image_files': [
                                os.path.join(cycle.image_dir, f) for f in batch
                            ]
                        },
                        'outputs': {
                            'stats_files': [
                                os.path.join(
                                    cycle.stats_dir,
                                    self.stats_file_format_string.format(
                                        channel=channels[i])
                                )
                            ]
                        },
                        'channel': channels[i],
                        'cycle': cycle.index,
                        'tpoint': cycle.tpoint
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
        image_files = batch['inputs']['image_files']
        logger.info('calculate illumination statistics')
        with ImageReader() as reader:
            img = reader.read(image_files[0])
            stats = OnlineStatistics(image_dimensions=img.shape)
            pctl = OnlinePercentile()
            for f in image_files:
                logger.debug('update statistics for image: %s',
                             os.path.basename(f))
                img = reader.read(f)
                stats.update(img)
                pctl.update(img)
        stats_file = batch['outputs']['stats_files'][0]
        logger.info('write calculated statistics to file')
        with DatasetWriter(stats_file, truncate=True) as writer:
            writer.write('/stats/mean', data=stats.mean)
            writer.write('/stats/std', data=stats.std)
            writer.write('/stats/percentile', data=pctl.percentile)
            writer.write('/metadata/cycle', data=batch['cycle'])
            writer.write('/metadata/tpoint', data=batch['tpoint'])
            writer.write('/metadata/channel', data=batch['channel'])

    @utils.notimplemented
    def collect_job_output(self, batch):
        pass
