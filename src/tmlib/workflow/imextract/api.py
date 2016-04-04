import os
import numpy as np
import logging
import collections

import tmlib.models
from tmlib.utils import notimplemented
from tmlib.readers import BFImageReader
from tmlib.image import ChannelImage
from tmlib.workflow.api import ClusterRoutines

logger = logging.getLogger(__name__)


class ImageExtractor(ClusterRoutines):

    '''Class for extraction of pixel arrays (planes) stored in image files using
    `python-bioformats <https://github.com/CellProfiler/python-bioformats>`_.
    The extracted arrays are written to PNG files.
    '''

    def __init__(self, experiment_id, verbosity):
        '''
        Initialize an instance of class ImageExtractor.

        Parameters
        ----------
        experiment_id: int
            ID of the processed experiment
        verbosity: int
            logging level
        '''
        super(ImageExtractor, self).__init__(experiment_id, verbosity)

    def create_batches(self, args):
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
        with tmlib.models.utils.Session() as session:
            image_files = session.query(tmlib.models.ChannelImageFile).\
                join(tmlib.models.Acquisition).\
                join(tmlib.models.Plate).\
                join(tmlib.models.Experiment).\
                filter(tmlib.models.Experiment.id == self.experiment_id).\
                all()

            batches = self._create_batches(image_files, args.batch_size)
            for image_file_subset in batches:
                job_count += 1
                job_descriptions['run'].append({
                    'id': job_count,
                    'inputs': {
                        'microscope_image_files': [
                            [
                                os.path.join(
                                    im_file.acquisition.microscope_images_location,
                                    f
                                )
                                for f in im_file.file_map['files']
                            ]
                            for im_file in image_file_subset
                        ]
                    },
                    'outputs': {
                        'channel_image_files': [
                            os.path.join(
                                im_file.cycle.channel_images_location,
                                im_file.name
                            )
                            for im_file in image_file_subset
                        ]
                    },
                    'series': [
                        im_file.file_map['series']
                        for im_file in image_file_subset
                    ],
                    'planes': [
                        im_file.file_map['planes']
                        for im_file in image_file_subset
                    ],
                    'channel_image_files_ids': [
                        im_file.id
                        for im_file in image_file_subset
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
            with tmlib.models.utils.Session() as session:
                for i, filenames in enumerate(batch['inputs']['microscope_image_files']):
                    planes = list()
                    for j, f in enumerate(filenames):
                        logger.info(
                            'extract image from file: %s', os.path.basename(f)
                        )
                        plane_ix = batch['planes'][i][j]
                        series_ix = batch['series'][i][j]
                        planes.append(
                            reader.read_subset(
                                f, plane=plane_ix, series=series_ix
                            )
                        )

                    dtype = planes[0].dtype
                    dims = planes[0].shape
                    stack = np.zeros(
                        (len(planes), dims[0], dims[1]), dtype=dtype
                    )
                    # If intensity projection should be performed there will
                    # be multiple planes per output filename and the stack will
                    # be multi-dimensional, i.e. stack.shape[0] > 1
                    for z in xrange(len(planes)):
                        stack[z, :, :] = planes[z]
                    img = ChannelImage(np.max(stack, axis=0))
                    # Write plane (2D single-channel image) to file
                    output_file = session.query(tmlib.models.ChannelImageFile).\
                        get(batch['channel_image_files_ids'][i])
                    logger.info('extracted image: %s', output_file.name)
                    output_file.put(img)
                    session.flush()

    @notimplemented
    def collect_job_output(self, batch):
        pass


def factory(experiment_id, verbosity, **kwargs):
    '''Factory function for the instantiation of a `imextract`-specific
    implementation of the :py:class:`tmlib.workflow.api.ClusterRoutines`
    abstract base class.

    Parameters
    ----------
    experiment_id: int
        ID of the processed experiment
    verbosity: int
        logging level
    **kwargs: dict
        ignored keyword arguments

    Returns
    -------
    tmlib.workflow.metaextract.api.ImageExtractor
        API instance
    '''
    return ImageExtractor(experiment_id, verbosity)
