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
        '''Creates job descriptions for parallel processing.

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
            file_mappings = session.query(tmlib.models.ImageFileMapping).\
                join(tmlib.models.Acquisition).\
                join(tmlib.models.Plate).\
                filter(tmlib.models.Plate.experiment_id == self.experiment_id).\
                all()

            batches = self._create_batches(file_mappings, args.batch_size)
            for batch in batches:
                job_count += 1
                job_descriptions['run'].append({
                    'id': job_count,
                    'inputs': {
                        'microscope_image_files': [
                            [
                                os.path.join(
                                    fmapping.acquisition.
                                    microscope_images_location,
                                    f
                                )
                                for f in fmapping.map['files']
                            ]
                            for fmapping in batch
                        ]
                    },
                    'outputs': {
                        'channel_image_files': [
                            os.path.join(
                                fmapping.cycle.channel_images_location,
                                tmlib.models.ChannelImageFile.FILENAME_FORMAT.
                                format(
                                    t=fmapping.tpoint,
                                    w=fmapping.site.well.name,
                                    y=fmapping.site.y, x=fmapping.site.x,
                                    c=fmapping.wavelength, z=fmapping.zplane
                                )
                            )
                            for fmapping in batch
                        ]
                    },
                    'image_file_mapping_ids': [
                        fmapping.id for fmapping in batch
                    ]
                })

        return job_descriptions

    def run_job(self, batch):
        '''Extracts individual planes from microscope image files and writes
        each to a separate file.

        Parameters
        ----------
        batch: dict
            job description
        '''
        with BFImageReader() as reader:
            file_mapping_ids = batch['image_file_mapping_ids']
            for i, fid in enumerate(file_mapping_ids):
                filenames = batch['inputs']['microscope_image_files'][i]
                with tmlib.models.utils.Session() as session:
                    fmapping = session.query(tmlib.models.ImageFileMapping).\
                        get(fid)
                    planes = list()
                    for j, f in enumerate(filenames):
                        logger.info(
                            'extract image from file: %s', os.path.basename(f)
                        )
                        plane_ix = fmapping.map['planes'][j]
                        series_ix = fmapping.map['series'][j]
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
                    image_file = session.get_or_create(
                        tmlib.models.ChannelImageFile,
                        tpoint=fmapping.tpoint, zplane=fmapping.zplane,
                        site_id=fmapping.site_id, cycle_id=fmapping.cycle_id,
                        channel_id=fmapping.channel_id
                    )
                    logger.info('stored in image file: %s', image_file.name)
                    image_file.put(img)

    def delete_previous_job_output(self):
        '''Deletes all instances of class
        :py:class:`tmlib.models.ChannelImageFile`,
        :py:class:`tmlib.models.IllumstatsFile`,
        :py:class:`tmlib.models.ChannelLayer`, and
        :py:class:`tmlib.models.MapobjectsType` as well as all children for
        the processed experiment.
        '''
        with tmlib.models.utils.Session() as session:

            image_files = session.query(tmlib.models.ChannelImageFile).\
                join(tmlib.models.Cycle).\
                join(tmlib.models.Plate).\
                filter(tmlib.models.Plate.experiment_id == self.experiment_id).\
                all()
            for f in image_files:
                logger.debug('delete channel image file: %r', f)
                session.delete(f)

            illumstats_files = session.query(tmlib.models.IllumstatsFile).\
                join(tmlib.models.Cycle).\
                join(tmlib.models.Plate).\
                filter(tmlib.models.Plate.experiment_id == self.experiment_id).\
                all()
            for f in illumstats_files:
                logger.debug('delete illumination statistics file: %r', f)
                session.delete(f)

            channel_layers = session.query(tmlib.models.ChannelLayer).\
                join(tmlib.models.Channel).\
                filter(tmlib.models.Channel.experiment_id == self.experiment_id).\
                all()
            for l in channel_layers:
                logger.debug('delete channel layer: %r', l)
                session.delete(l)

            mapobject_types = session.query(tmlib.models.MapobjectType).\
                filter(tmlib.models.MapobjectType.experiment_id == self.experiment_id).\
                all()
            for m in mapobject_types:
                logger.debug('delete mapobject type: %r', m)
                session.delete(m)

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
