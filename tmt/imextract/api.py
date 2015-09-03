import os
import numpy as np
from cached_property import cached_property
import yaml
from .. import imageutils
from .. import utils
from ..format import supported_formats
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

    def __init__(self, input_dir, output_dir, metadata_file,
                 logging_level='critical'):
        '''
        Initialize an instance of class ImageExtractor.

        Parameters
        ----------
        input_dir: str
            absolute path to the directory that contains the image files,
            from which individual images should be extracted (converted)
        output_dir: str
            absolute path to the directory where files containing the extracted
            images should be stored
        metadata_file: str
            absolute path to the file that contains the metadata for each
            output image
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
        super(ImageExtractor, self).__init__(logging_level)
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.metadata_file = metadata_file
        if not os.path.exists(self.output_dir):
            os.mkdir(self.output_dir)
        if not os.path.exists(self.metadata_file):
            raise OSError('Metadata file does not exist. You can create it '
                          'using the "format" package.')

    @cached_property
    def metadata(self):
        '''
        Read metadata information from file and cache it.

        Returns
        -------
        List[ChannelImageMetadata]
            metadata for each output image
        '''
        metadata = utils.read_json(self.metadata_file)
        self._metadata = [ChannelImageMetadata(md) for md in metadata.values()]
        return self._metadata

    @property
    def name(self):
        '''
        Returns
        -------
        str
            name of the program in lower case letters
        '''
        self._name = self.__class__.__name__.lower()
        return self._name

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
        self._log_dir = os.path.join(os.path.dirname(self.output_dir),
                                     'log_{name}'.format(self.name))
        return self._log_dir

    def print_supported_formats(self):
        '''
        Print supported file formats to standard output in YAML format.
        '''
        print yaml.dump(supported_formats, default_flow_style=False)

    def create_joblist(self, batch_size):
        '''
        Create a list of information required for the creation and processing
        of individual jobs.

        Parameters
        ----------
        batch_size: int, optional
            number of files that should be processed together as one job
        '''
        batches = self.create_batches(self.metadata.values(), batch_size)
        joblist = [{'id': i+1, 'metadata': [b.serialize() for b in batch]}
                   for i, batch in enumerate(batches)]
        self.write_joblist(joblist)
        return joblist

    def build_command(self, batch, cfg_file=None):
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
        command = [
            'extract', 'image', '--job', str(job_id)
        ]
        if cfg_file:
            command += ['--cfg', cfg_file]
        return command

    def run(self, batch):
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
            for b in batch:
                md = b['metadata']
                # Perform maximum intensity projection to reduce
                # dimensionality to 2D if there is more than 1 z-stack
                stack = np.empty((md['dimensions'][0], md['dimensions'][1],
                                  len(md['planes'])), dtype=md['dtype'])
                for z in md['planes']:
                    f_path = os.path.join(self.input_dir,
                                          md['original_filename'])
                    stack[:, :, z] = reader.read_subset(f_path, plane=z,
                                                        series=b['series'])
                img = np.max(stack, axis=2)
                # Write plane (2D single-channel image) to file
                filename = os.path.join(self.output_dir, md['filename'])
                imageutils.save_image_png(img, filename)
