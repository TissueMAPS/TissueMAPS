import os
import numpy as np
from .. import image_utils
from ..image_readers import BioformatsImageReader
from ..cluster import ClusterRoutines


class ImageExtractor(ClusterRoutines):

    '''
    Class for extraction of pixel arrays (planes) stored in image files using
    the Bio-Formats library via
    `python-bioformats <https://github.com/CellProfiler/python-bioformats>`_.
    The extracted arrays are written to PNG files. This is done to save disk
    space due to (lossless) file compression and for downstream compatibility,
    since not many libraries are able to read images from the original file
    formats (often extended TIFF formats).
    '''

    def __init__(self, experiment_dir, prog_name):
        '''
        Initialize an instance of class ImageExtractor.

        Parameters
        ----------
        experiment_dir: str
            absolute path to experiment directory
        prog_name: str
            name of the corresponding program (command line interface)

        See also
        --------
        `tmlib.cfg`_
        '''
        super(ImageExtractor, self).__init__(experiment_dir, prog_name)
        self.experiment_dir = experiment_dir
        self.prog_name = prog_name

    def _create_output_dirs(self):
        for cycle in self.cycles:
            if not os.path.exists(cycle.image_dir):
                os.mkdir(cycle.image_dir)

    def create_job_descriptions(self, **kwargs):
        '''
        Create a list of information required for the creation and processing
        of individual jobs.

        Parameters
        ----------
        **kwargs: dict
            additional input arguments as key-value pairs:
            * "batch_size": number of images per job (*int*)

        Returns
        -------
        Dict[str, List[dict] or dict]
            job descriptions
        '''
        joblist = dict()
        joblist['run'] = list()
        count = 0
        for cycle in self.cycles:
            md_batches = self._create_batches(cycle.image_metadata,
                                              kwargs['batch_size'])
            for batch in md_batches:
                count += 1
                joblist['run'].append({
                    'id': count,
                    'inputs': {
                        'image_files': [
                            os.path.join(cycle.image_upload_dir,
                                         md.original_filename)
                            for md in batch
                        ]
                    },
                    'outputs': {
                        'image_files': [
                            os.path.join(cycle.image_dir, md.name)
                            for md in batch
                        ]
                    },
                    'metadata': [md.serialize() for md in batch],
                    'cycle': cycle.name

                })
        return joblist

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
                    filename = batch['inputs']['image_files'][i]
                    stack[:, :, z] = reader.read_subset(
                                        filename, plane=z,
                                        series=md['original_series'])
                img = np.max(stack, axis=2)
                # Write plane (2D single-channel image) to file
                filename = batch['outputs']['image_files'][i]
                image_utils.save_image_png(img, filename)

    def collect_job_output(self, batch):
        raise AttributeError('"%s" object doesn\'t have a "collect_job_output"'
                             ' method' % self.__class__.__name__)

    def apply_statistics(self, joblist, wells, sites, channels, output_dir,
                         **kwargs):
        raise AttributeError('"%s" object doesn\'t have a "apply_statistics"'
                             ' method' % self.__class__.__name__)
