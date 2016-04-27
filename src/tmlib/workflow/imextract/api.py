import os
import numpy as np
import pandas as pd
import logging
import collections

import tmlib.models as tm
from tmlib.utils import notimplemented
from tmlib.readers import BFImageReader
from tmlib.image import ChannelImage
from tmlib.workflow.api import ClusterRoutines
from tmlib.workflow.registry import api

logger = logging.getLogger(__name__)


@api('imextract')
class ImageExtractor(ClusterRoutines):

    '''Class for extraction of pixel arrays (planes) stored in image files using
    `python-bioformats <https://github.com/CellProfiler/python-bioformats>`_.
    The extracted arrays are written to PNG files.
    '''

    def __init__(self, experiment_id, verbosity):
        '''
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
        with tm.utils.Session() as session:
            file_mappings = session.query(tm.ImageFileMapping).\
                join(tm.Acquisition).\
                join(tm.Plate).\
                filter(tm.Plate.experiment_id == self.experiment_id).\
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
                                tm.ChannelImageFile.FILENAME_FORMAT.
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

            job_descriptions['collect'] = {
                'inputs': dict(),
                'outputs': dict()
            }

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
                with tm.utils.Session() as session:
                    fmapping = session.query(tm.ImageFileMapping).\
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
                        tm.ChannelImageFile,
                        tpoint=fmapping.tpoint, zplane=fmapping.zplane,
                        site_id=fmapping.site_id, cycle_id=fmapping.cycle_id,
                        channel_id=fmapping.channel_id
                    )
                    logger.info('stored in image file: %s', image_file.name)
                    image_file.put(img)

    def delete_previous_job_output(self):
        '''Deletes all instances of class
        :py:class:`tm.ChannelImageFile`,
        :py:class:`tm.IllumstatsFile`,
        :py:class:`tm.ChannelLayer`, and
        :py:class:`tm.MapobjectsType` as well as all children for
        the processed experiment.
        '''
        with tm.utils.Session() as session:

            cycle_ids = session.query(tm.Cycle.id).\
                join(tm.Plate).\
                filter(tm.Plate.experiment_id == self.experiment_id).\
                all()
            cycle_ids = [p[0] for p in cycle_ids]

        if cycle_ids:

            with tm.utils.Session() as session:

                logger.info('delete existing channel image files')
                session.query(tm.ChannelImageFile).\
                    filter(tm.ChannelImageFile.cycle_id.in_(cycle_ids)).\
                    delete()

    def collect_job_output(self, batch):
        '''Omits channel image files that do not exist across all cycles.

        Parameters
        ----------
        batch: dict
            job description
        '''
        with tm.utils.Session() as session:
            metadata = pd.DataFrame(
                session.query(
                    tm.ChannelImageFile.id,
                    tm.ChannelImageFile.site_id,
                    tm.ChannelImageFile.cycle_id
                ).
                join(tm.Channel).
                filter(tm.Channel.experiment_id == self.experiment_id).
                all()
            )
            cycle_ids = np.unique(metadata.cycle_id)
            site_group = metadata.groupby('site_id')
            for i, sg in site_group:
                if len(np.setdiff1d(cycle_ids, sg.cycle_id.values)) > 0:
                    sites_to_omit = session.query(tm.ChannelImageFile).\
                        filter(tm.ChannelImageFile.id.in_(sg.id.values)).\
                        all()
                    for site in sites_to_omit:
                        site.omitted = True
                    session.add_all(sites_to_omit)

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
