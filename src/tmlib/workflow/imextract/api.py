import os
import numpy as np
import logging
import collections
from .. import utils
from ..readers import BFImageReader
from ..api import ClusterRoutines
from ..writers import ImageWriter

logger = logging.getLogger(__name__)


class ImageExtractor(ClusterRoutines):

    '''
    Class for extraction of pixel arrays (planes) stored in image files using
    `python-bioformats <https://github.com/CellProfiler/python-bioformats>`_.
    The extracted arrays are written to PNG files.
    '''

    def __init__(self, experiment, step_name, verbosity, **kwargs):
        '''
        Initialize an instance of class ImageExtractor.

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
        super(ImageExtractor, self).__init__(
                experiment, step_name, verbosity)

    def _create_output_dirs(self):
        for cycle in self.cycles:
            if not os.path.exists(cycle.image_dir):
                os.mkdir(cycle.image_dir)

    def create_job_descriptions(self, args):
        '''
        Create a list of information required for the creation and processing
        of individual jobs.

        Parameters
        ----------
        args: tmlib.imextract.args.ImextractInitArgs
            step-specific arguments

        Returns
        -------
        Dict[str, List[dict] or dict]
            job descriptions
        '''
        job_count = 0
        job_descriptions = collections.defaultdict(list)
        for source in self.experiment.sources:
            mapper = source.image_mapping
            ix_batches = self._create_batches(range(len(mapper)),
                                              args.batch_size)

            for indices in ix_batches:
                job_count += 1
                job_descriptions['run'].append({
                    'id': job_count,
                    'inputs': {
                        'image_files': [
                            [
                                os.path.join(self.experiment.sources_dir, f)
                                for f in mapper[ix].files
                            ]
                            for ix in indices
                        ]
                    },
                    'outputs': {
                        'image_files': [
                            os.path.join(
                                self.experiment.plates_dir,
                                mapper[ix].ref_file)
                            for ix in indices
                        ]
                    },
                    'series': [
                        mapper[ix].series for ix in indices
                    ],
                    'planes': [
                        mapper[ix].planes for ix in indices
                    ]
                })

        return job_descriptions

    def run_job(self, batch):
        '''
        Extract individual planes from an image file and write each of them
        to a separate PNG file.

        Parameters
        ----------
        batch: dict
            joblist element, i.e. description of a single job
        '''
        with BFImageReader() as reader:
            for i, filenames in enumerate(batch['inputs']['image_files']):
                planes = list()
                for j, f in enumerate(filenames):
                    logger.info('extract image from file: %s',
                                os.path.basename(f))
                    plane_ix = batch['planes'][i][j]
                    series_ix = batch['series'][i][j]
                    planes.append(reader.read_subset(
                            f, plane=plane_ix, series=series_ix))

                dtype = planes[0].dtype
                dims = planes[0].shape
                stack = np.zeros((len(planes), dims[0], dims[1]), dtype=dtype)
                # If intensity projection should be performed there will
                # be multiple planes per output filename and the stack will
                # be multi-dimensional, i.e. stack.shape[0] > 1
                for z in xrange(len(planes)):
                    stack[z, :, :] = planes[z]
                img = np.max(stack, axis=0)
                # Write plane (2D single-channel image) to file
                output_filename = batch['outputs']['image_files'][i]
                logger.info('extracted image: %s',
                            os.path.basename(output_filename))
                with ImageWriter() as writer:
                    writer.write(output_filename, img)

    @utils.notimplemented
    def collect_job_output(self, batch):
        pass

    @utils.notimplemented
    def apply_statistics(self, output_dir, plates, wells, sites, channels,
                         tpoints, zplanes, **kwargs):
        pass
