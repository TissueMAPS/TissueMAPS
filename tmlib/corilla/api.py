import os
import re
import logging
from .stats import OnlineStatistics
from ..writers import DatasetWriter
from ..readers import NumpyImageReader
from ..cluster import ClusterRoutines

logger = logging.getLogger(__name__)


class IllumstatsGenerator(ClusterRoutines):

    '''
    Class for calculating illumination statistics.
    '''

    def __init__(self, experiment, prog_name, verbosity):
        '''
        Initialize an instance of class IllumstatsGenerator.

        Parameters
        ----------
        experiment: tmlib.experiment.Experiment
            configured experiment object
        prog_name: str
            name of the corresponding program (command line interface)
        verbosity: int
            logging level

        Returns
        -------
        tmlib.corilla.api.IllumstatsGenerator
        '''
        super(IllumstatsGenerator, self).__init__(
                experiment, prog_name, verbosity)
        self.experiment = experiment
        self.prog_name = prog_name
        self.verbosity = verbosity

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

    def create_job_descriptions(self, **kwargs):
        '''
        Create job descriptions for parallel computing.

        Parameters
        ----------
        **kwargs: dict
            empty - no additional arguments

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
                md = cycle.image_metadata_table

                # Group image files per channel
                channels = list(set(md['channel_ix'].tolist()))
                img_batches = list()
                for c in channels:
                    files = md[(md['channel_ix'] == c)]['name'].tolist()
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
                            'stats_file':
                                os.path.join(
                                    cycle.stats_dir,
                                    self.stats_file_format_string.format(
                                        channel_ix=channels[i]))
                        },
                        'channel': channels[i],
                        'cycle': cycle.index
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
        with NumpyImageReader() as reader:
            img = reader.read(image_files[0])
            stats = OnlineStatistics(image_dimensions=img.shape)
            for f in image_files:
                logger.debug('update statistics for image: %s',
                             os.path.basename(f))
                img = reader.read(f)
                stats.update(img)
        stats_file = batch['outputs']['stats_file']
        logger.info('write calculated statistics to file')
        with DatasetWriter(stats_file, truncate=True) as writer:
            writer.write('/images/mean', data=stats.mean)
            writer.write('/images/std', data=stats.std)
            writer.write('/metadata/tpoint_ix', data=batch['cycle'])
            writer.write('/metadata/channel_ix', data=batch['channel'])

    def apply_statistics(self, output_dir, **kwargs):
        '''
        Apply the calculated statistics to images in order to correct them for
        illumination artifacts. A subset of images that should be corrected can
        be selected based on following criteria:
            * **plates**: plate names (*List[str]*)
            * **wells**: cycle names (*List[str]*)
            * **channels**: channel indices (*List[int]*)
            * **zplanes**: z-plane indices (*List[int]*)

        Parameters
        ----------
        output_dir: str
            absolute path to directory where the corrected images should be
            written to
        **kwargs: dict
            additional arguments as key-value pairs: selection criteria
        '''
        logger.info('correct images for illumination artifacts')
        for plate in self.experiment.plates:
            if kwargs['plates']:
                if plate.name not in kwargs['plates']:
                    continue
            for cycle in plate.cycles:
                if kwargs['tpoints']:
                    if cycle.index not in kwargs['tpoints']:
                        continue
                md = cycle.image_metadata_table
                sld = md.copy()
                if kwargs['sites']:
                    sld = sld[sld['site_ix'].isin(kwargs['sites'])]
                if kwargs['wells']:
                    sld = sld[sld['well_name'].isin(kwargs['wells'])]
                if kwargs['channels']:
                    sld = sld[sld['channel_ix'].isin(kwargs['channels'])]
                if kwargs['zplanes']:
                    sld = sld[sld['zplane_ix'].isin(kwargs['zplanes'])]
                selected_channels = list(set(sld['channel_ix'].tolist()))
                for c in selected_channels:
                    stats = cycle.illumstats_images[c]
                    sld = sld[sld['channel_ix'] == c]
                    image_indices = sld['name'].index
                    for i in image_indices:
                        image = cycle.images[i]
                        filename = image.metadata.name
                        logger.info('correct image: %s', filename)
                        corrected_image = image.correct(stats)
                        suffix = os.path.splitext(image.metadata.name)[1]
                        output_filename = re.sub(
                            r'\%s$' % suffix, '_corrected%s' % suffix,
                            filename)
                        output_filename = os.path.join(
                            output_dir, output_filename)
                        corrected_image.save_as_png(output_filename)

    def collect_job_output(self, batch):
        raise AttributeError('"%s" object doesn\'t have a "collect_job_output"'
                             ' method' % self.__class__.__name__)
