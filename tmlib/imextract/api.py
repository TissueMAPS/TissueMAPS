import os
import numpy as np
import logging
from copy import copy
from .. import image_utils
from .. import utils
from ..readers import BioformatsImageReader
from ..cluster import ClusterRoutines
from ..writers import ImageMetadataWriter
from ..errors import NotSupportedError

logger = logging.getLogger(__name__)


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

    def __init__(self, experiment, prog_name):
        '''
        Instantiate an instance of class ImageExtractor.

        Parameters
        ----------
        experiment: Experiment
            configured experiment object
        prog_name: str
            name of the corresponding program (command line interface)
        '''
        super(ImageExtractor, self).__init__(experiment, prog_name)
        self.experiment = experiment
        self.prog_name = prog_name
        self._update_experiment_layout()

    def _update_experiment_layout(self):
        time_points = set([md.time for md in self.cycles[0].image_metadata])
        if len(self.cycles) > 1 and len(time_points) > 1:
            raise NotSupportedError('Only one time points per cycle supported')
        elif len(self.cycles) == 1 and len(time_points) > 1:
            # Create a separate cycle for each time point
            for t in sorted(list(time_points)):
                metadata = [
                    md.serialize()
                    for md in self.cycles[0].image_metadata if md.time == t
                ]
                if t > 0:
                    cycle = self.experiment.create_additional_cycle()
                else:
                    cycle = self.cycles[0]
                with ImageMetadataWriter(cycle.metadata_dir) as writer:
                    writer.write(cycle.image_metadata_file, metadata)

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
            if kwargs['projection']:
                metadata = self._update_metadata_for_projection(cycle)
            else:
                metadata = cycle.image_metadata
            md_batches = self._create_batches(metadata,
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
                    'dimensions': [md.original_dimensions for md in batch],
                    'dtype': [md.original_dtype for md in batch],
                    'series': [md.original_series for md in batch],
                    'planes': [md.original_planes for md in batch],
                    'metadata': [md.serialize() for md in batch],
                    'cycle': cycle.name

                })
        return joblist

    @staticmethod
    def _update_metadata_for_projection(cycle):
        stacks = set([md.stack for md in cycle.image_metadata])
        if len(stacks) == 1:
            return cycle.image_metadata
        # Combine metadata for z-stacks
        sites = set([md.site for md in cycle.image_metadata])
        time_points = set([md.time for md in cycle.image_metadata])
        channels = set([md.channel for md in cycle.image_metadata]) 
        modified_metadata = list()
        for s in sites:
            for c in channels:
                for t in time_points:
                    matching_metadata = [
                        md for md in cycle.image_metadata
                        if md.site == s
                        and md.channel == c and md.time == t
                    ]
                    mod_md = copy(matching_metadata[0])
                    mod_md.original_planes = utils.flatten([
                        md.original_planes for md in matching_metadata
                    ])
                    mod_md.stack = 1
                    modified_metadata.append(mod_md)
        # Update the corresponding file, too
        with ImageMetadataWriter(cycle.metadata_dir) as writer:
            writer.write(cycle.image_metadata_file,
                         [md.serialize() for md in modified_metadata])
        return modified_metadata

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
            for i, filename in enumerate(batch['outputs']['image_files']):
                focal_planes = batch['planes'][i]
                stack = np.empty((len(focal_planes),
                                  batch['dimensions'][i][0],
                                  batch['dimensions'][i][1]),
                                 dtype=batch['dtype'][i])
                # If intensity projection should be performed there will
                # be multiple planes per output filename and the stack will
                # be multi-dimensional, i.e. stack.shape[0] > 1
                for z in xrange(len(focal_planes)):
                    stack[z, :, :] = reader.read_subset(
                                        batch['inputs']['image_files'][i],
                                        plane=z, series=batch['series'][i])
                img = np.max(stack, axis=0)
                # Write plane (2D single-channel image) to file
                image_utils.save_image_png(img, filename)

    def collect_job_output(self, batch):
        raise AttributeError('"%s" object doesn\'t have a "collect_job_output"'
                             ' method' % self.__class__.__name__)

    def apply_statistics(self, joblist, wells, sites, channels, output_dir,
                         **kwargs):
        raise AttributeError('"%s" object doesn\'t have a "apply_statistics"'
                             ' method' % self.__class__.__name__)
