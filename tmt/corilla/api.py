import os
import re
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

    def __init__(self, cycle, stats_file_format_string, prog_name,
                 logging_level='critical'):
        '''
        Initialize an instance of class IllumstatsCalculator.

        Parameters
        ----------
        cycle: Cycle
            cycle object that holds information about the content of the cycle
            directory
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
        self.cycle = cycle
        if not os.path.exists(self.cycle.stats_dir):
            os.mkdir(self.cycle.stats_dir)
        self.stats_file_format_string = stats_file_format_string

    @property
    def log_dir(self):
        '''
        Returns
        -------
        str
            directory where log files should be stored

        Note
        ----
        The directory will be sibling to the output directory.
        '''
        self._log_dir = os.path.join(os.path.dirname(self.cycle.stats_dir),
                                     'log_%s' % self.prog_name)
        return self._log_dir

    def create_joblist(self, **kwargs):
        '''
        Create a list of information required for the creation and processing
        of individual jobs.

        Parameters
        ----------
        **kwargs: dict
            empty - no additional arguments
        '''
        image_metadata = self.cycle.image_metadata
        channels = list(set([md.channel for md in image_metadata]))
        img_batches = list()
        for c in channels:
            image_files = [md.name for md in image_metadata if md.channel == c]
            img_batches.append(image_files)

        joblist = [{
                'id': i+1,
                'inputs': {
                    'image_files':
                        [os.path.join(self.cycle.image_dir, f) for f in batch]
                },
                'outputs': {
                    'stats_file':
                        os.path.join(self.cycle.stats_dir,
                                     self.stats_file_format_string.format(
                                            cycle=self.cycle.name,
                                            channel=channels[i]))
                },
                'channel': channels[i],
            } for i, batch in enumerate(img_batches)]
        return joblist

    def build_command(self, batch):
        '''
        Build a command for GC3Pie submission. For further information on
        the structure of the command see
        `subprocess <https://docs.python.org/2/library/subprocess.html>`_.

        Parameter
        ---------
        batch: Dict[str, int or List[str]]
            joblist element

        Returns
        -------
        List[str]
            substrings of the command call
        '''
        job_id = batch['id']
        command = ['corilla']
        command += ['run', '-j', str(job_id), self.cycle.dir]
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
        for b in batches:
            image_files = [f for f in b['inputs']['image_files']]
            stats_file = b['outputs']['stats_file']
            stats = IllumstatsImages.create_from_file(stats_file, 'numpy')
            # TODO: an additional factory
            for f in image_files:
                metadata = [md for md in self.cycle.image_metadata
                            if md.name == os.path.basename(f)][0]
                if sites:
                    if metadata.site not in sites:
                        continue
                if wells and metadata.well:  # may not be a well plate
                    if metadata.well not in wells:
                        continue
                image = ChannelImage.create_from_file(f, metadata, 'numpy')
                corrected_image = image.correct(stats.mean, stats.std)
                suffix = os.path.splitext(image.metadata.name)[1]
                output_filename = re.sub(r'\%s$' % suffix,
                                         '_corrected%s' % suffix,
                                         image.metadata.name)
                output_filename = os.path.join(output_dir, output_filename)
                corrected_image.save_as_png(output_filename)
