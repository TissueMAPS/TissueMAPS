import os
import numpy as np
from cached_property import cached_property
from .. import imageutils
from .. import utils
from ..metadata import ChannelImageMetadata
from ..image_readers import BioformatsImageReader
from ..cluster import ClusterRoutine


class ImageExtractor(ClusterRoutine):

    '''
    Class for extraction of pixel arrays (planes) stored in image files using
    the Bio-Formats library via
    `python-bioformats <https://github.com/CellProfiler/python-bioformats>`_.
    The extracted arrays are written to PNG files. This is done to save disk
    space due to (lossless) file compression and for downstream compatibility,
    since not many libraries are able to read images from the original file
    formats (often extended TIFF formats).
    '''

    def __init__(self, cycle, prog_name, logging_level='critical'):
        '''
        Initialize an instance of class ImageExtractor.

        Parameters
        ----------
        cycle: Cycle
            cycle object that holds information about the content of the cycle
            directory
        prog_name: str
            name of the corresponding program (command line interface)
        logging_level: str, optional
            configuration of GC3Pie logger; either "debug", "info", "warning",
            "error" or "critical" (defaults to ``"critical"``)

        Note
        ----
        `output_dir` will be created if it doesn't exist.

        Raises
        ------
        OSError
            when `metadata_file` does not exist
        '''
        super(ImageExtractor, self).__init__(prog_name, logging_level)
        self.cycle = cycle
        if not os.path.exists(self.cycle.image_dir):
            os.mkdir(self.cycle.image_dir)
        if not os.path.exists(os.path.join(self.cycle.metadata_dir,
                                           self.cycle.image_metadata_file)):
            raise OSError('Metadata file does not exist. You can create it '
                          'using the "format" package.')
        self.prog_name = prog_name

    @cached_property
    def metadata(self):
        '''
        Read metadata information from file and cache it.

        Returns
        -------
        List[ChannelImageMetadata]
            metadata for each output image
        '''
        filename = os.path.join(self.cycle.metadata_dir,
                                self.cycle.image_metadata_file)
        metadata = utils.read_json(filename)
        self._metadata = [ChannelImageMetadata(md) for md in metadata.values()]
        return self._metadata

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
        self._log_dir = os.path.join(os.path.dirname(self.cycle.image_dir),
                                     'log_{name}'.format(name=self.prog_name))
        return self._log_dir

    def create_joblist(self, batch_size=None, cfg_file=None):
        '''
        Create a list of information required for the creation and processing
        of individual jobs.

        Parameters
        ----------
        batch_size: int, optional
            number of files that should be processed together as one job
        cfg_file: str, optional
            absolute path to custom configuration file
        '''
        md_batches = self._create_batches(self.metadata, batch_size)
        joblist = [{
                'id': i+1,
                'cfg_file': cfg_file,
                'inputs': [os.path.join(self.cycle.image_upload_dir,
                                        md.original_filename) for md in batch],
                'outputs': [os.path.join(self.cycle.image_dir,
                                         md.filename) for md in batch],
                'metadata': [md.serialize() for md in batch]

            } for i, batch in enumerate(md_batches)]
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
        cfg_file: str
            absolute path to configuration file

        Returns
        -------
        List[str]
            substrings of the command call
        '''
        job_id = batch['id']
        command = ['imextract']
        if batch['cfg_file']:
            command += ['--cfg', batch['cfg_file']]
        command += ['run', '--job', str(job_id), self.cycle.cycle_dir]
        return command

    def run_job(self, batch):
        '''
        For each channel, extract all corresponding planes, perform maximum
        intensity projection in case there are more than one plane per channel,
        and write each resulting 2D channel plane to a separate PNG file.

        Parameters
        ----------
        batch: dict
            joblist element, i.e. description of a single job
        '''
        with BioformatsImageReader() as reader:
            for i, md in enumerate(batch['metadata']):
                # Perform maximum intensity projection to reduce
                # dimensionality to 2D if there is more than 1 z-stack
                stack = np.empty((md['original_dimensions'][0],
                                  md['original_dimensions'][1],
                                  len(md['original_planes'])),
                                 dtype=md['original_dtype'])
                for z in md['original_planes']:
                    filename = batch['inputs'][i]
                    stack[:, :, z] = reader.read_subset(
                                        filename, plane=z,
                                        series=md['original_series'])
                img = np.max(stack, axis=2)
                # Write plane (2D single-channel image) to file
                filename = batch['outputs'][i]
                imageutils.save_image_png(img, filename)
