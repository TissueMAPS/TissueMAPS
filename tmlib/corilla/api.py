import os
import re
from .stats import OnlineStatistics
from ..writers import DatasetWriter
from ..image import ChannelImage
from ..image_readers import OpencvImageReader
from ..image import IllumstatsImages
from ..cluster import ClusterRoutines


class IllumstatsGenerator(ClusterRoutines):
    '''
    Class for calculating illumination statistics.
    '''

    def __init__(self, experiment, stats_file_format_string, prog_name,
                 verbosity=0):
        '''
        Initialize an instance of class IllumstatsGenerator.

        Parameters
        ----------
        experiment: Experiment
            experiment object that holds information about the content of the
            experiment directory
        image_file_format_string: str
            format string that specifies how the names of the statistics files
            should be formatted
        prog_name: str
            name of the corresponding program (command line interface)
        verbosity: int, optional
            logging level (default: ``0``)

        Note
        ----
        Creates directory where statistics files will be stored in case it
        doesn't exist.
        '''
        super(IllumstatsGenerator, self).__init__(
            experiment, prog_name, verbosity)
        self.experiment = experiment
        self.stats_file_format_string = stats_file_format_string

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
        joblist = dict()
        joblist['run'] = list()
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
                joblist['run'].append({
                    'id': count,
                    'inputs': {
                        'image_files': [
                            os.path.join(cycle.image_dir, f) for f in batch
                        ]
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
        with DatasetWriter(batch['outputs']['stats_file'], new=True) as f:
            f.write('/images/mean', data=stats.mean)
            f.write('/images/std', data=stats.std)
            f.write('/metadata/cycle', data=batch['cycle'])
            f.write('/metadata/channel', data=batch['channel'])

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
        batches = [b for b in joblist['run'] if b['channel'] in channels]
        # TODO: check whether channel names are valid
        for b in batches:
            image_files = [f for f in b['inputs']['image_files']]
            cycle = [
                cycle for cycle in self.cycles
                if cycle.name == b['cycle']
            ][0]
            stats = [
                stats for stats in cycle.stats_images
                if stats.metadata.channel == b['channel']
            ][0]
            for f in image_files:
                image = [
                    img for img in cycle.images
                    if img.metadata.name == os.path.basename(f)
                ][0]
                if sites:
                    if image.metadata.site not in sites:
                        continue
                if wells and image.metadata.well:  # may not be a well plate
                    if image.metadata.well not in wells:
                        continue
                corrected_image = image.correct(stats)
                suffix = os.path.splitext(image.metadata.name)[1]
                output_filename = re.sub(r'\%s$' % suffix,
                                         '_corrected%s' % suffix,
                                         image.metadata.name)
                output_filename = os.path.join(output_dir, output_filename)
                corrected_image.save_as_png(output_filename)

    def collect_job_output(self, batch):
        raise AttributeError('"%s" object doesn\'t have a "collect_job_output"'
                             ' method' % self.__class__.__name__)
