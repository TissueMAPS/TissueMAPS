import os
import re
from cached_property import cached_property
from .stats import OnlineStatistics
from ..writers import DatasetWriter
from ..image import ChannelImage
from ..image_readers import OpencvImageReader
from ..image import IllumstatsImages
from ..cluster import ClusterRoutine


class IllumstatsCalculator(ClusterRoutine):
    '''
    Class for calculating illumination statistics .
    '''

    def __init__(self, experiment, stats_file_format_string, prog_name,
                 logging_level='critical'):
        '''
        Initialize an instance of class IllumstatsCalculator.

        Parameters
        ----------
        experiment: Experiment
            cycle object that holds information about the content of the
            experiment directory
        image_file_format_string: str
            format string that specifies how the names of the statistics files
            should be formatted
        prog_name: str
            name of the corresponding program (command line interface)
        logging_level: str, optional
            configuration of GC3Pie logger; either "debug", "info", "warning",
            "error" or "critical" (defaults to ``"critical"``)

        Note
        ----
        Creates directory where statistics files will be stored in case it
        doesn't exist.
        '''
        super(IllumstatsCalculator, self).__init__(prog_name, logging_level)
        self.experiment = experiment
        self.stats_file_format_string = stats_file_format_string

    @property
    def log_dir(self):
        '''
        Returns
        -------
        str
            directory where log files should be stored
        '''
        self._log_dir = os.path.join(self.experiment.dir,
                                     'log_%s' % self.prog_name)
        return self._log_dir

    @cached_property
    def cycles(self):
        '''
        Returns
        -------
        List[Wellplate or Slide]
            cycle objects
        '''
        self._cycles = self.experiment.cycles
        return self._cycles

    def create_joblist(self, **kwargs):
        '''
        Create a list of information required for the creation and processing
        of individual jobs.

        Parameters
        ----------
        **kwargs: dict
            empty - no additional arguments
        '''
        joblist = list()
        count = 0
        for i, cycle in enumerate(self.cycles):
            channels = list(set([md.channel for md in cycle.image_metadata]))
            img_batches = list()
            for c in channels:
                image_files = [md.name for md in cycle.image_metadata
                               if md.channel == c]
                img_batches.append(image_files)

            for j, batch in enumerate(img_batches):
                count += 1
                joblist.append({
                    'id': count,
                    'inputs': {
                        'image_files':
                            [os.path.join(cycle.image_dir, f) for f in batch]
                    },
                    'outputs': {
                        'stats_file':
                            os.path.join(cycle.stats_dir,
                                         self.stats_file_format_string.format(
                                                cycle=cycle.name,
                                                channel=channels[j]))
                    },
                    'channel': channels[j],
                    'cycle': cycle.name
                })
        return joblist

    def _build_command(self, batch):
        job_id = batch['id']
        command = ['corilla']
        command.append(self.experiment.dir)
        command.extend(['run', '-j', str(job_id)])
        return command

    def run_job(self, batch):
        '''
        Calculate online statistics and write results to a HDF5 file.

        Parameters
        ----------
        batch: dict
            joblist element
        '''
        image_files = batch['inputs']['image_files']
        with OpencvImageReader() as reader:
            img = reader.read(image_files[0])
            stats = OnlineStatistics(image_dimensions=img.shape)
            for f in image_files:
                img = reader.read(f)
                stats.update(img)

        with DatasetWriter(batch['outputs']['stats_file']) as writer:
            writer.write_dataset('/data/mean', data=stats.mean)
            writer.write_dataset('/data/std', data=stats.std)
            writer.write_dataset('/metadata/cycle', data=self.cycle.name)
            writer.write_dataset('/metadata/channel', data=batch['channel'])

    def apply_statistics(self, joblist, wells, sites, channels, output_dir,
                         **kwargs):
        '''
        Apply calculated statistics to images in order to correct illumination
        artifacts.

        Parameters
        ----------
        wells: List[str]
            well identifiers of images that should be corrected
        sites: List[int]
            one-based site indices of images that should be corrected
        channels: List[str]
            channel names of images that should be corrected
        output_dir: str
            absolute path to directory where the corrected images should be
            stored
        **kwargs: dict
            empty - no additional arguments
        '''
        batches = [b for b in joblist if b['channel'] in channels]
        # TODO: check whether channel names are valid
        for b in batches:
            image_files = [f for f in b['inputs']['image_files']]
            stats_file = b['outputs']['stats_file']
            stats = IllumstatsImages.create_from_file(stats_file)
            for f in image_files:
                metadata = [cycle.image_metadata for cycle in self.cycles
                            if cycle.name == b['cycle']][0]
                image = [ChannelImage.create_from_file(f, md)
                         for md in metadata
                         if md.name == os.path.basename(f)][0]
                if sites:
                    if image.metadata.site not in sites:
                        continue
                if wells and image.metadata.well:  # may not be a well plate
                    if image.metadata.well not in wells:
                        continue
                corrected_image = image.correct(stats.mean, stats.std)
                suffix = os.path.splitext(image.metadata.name)[1]
                output_filename = re.sub(r'\%s$' % suffix,
                                         '_corrected%s' % suffix,
                                         image.metadata.name)
                output_filename = os.path.join(output_dir, output_filename)
                corrected_image.save_as_png(output_filename)

    def collect_job_output(self, joblist, **kwargs):
        pass
