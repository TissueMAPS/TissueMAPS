import os
import numpy as np
import pandas as pd
import logging
import collections
from sqlalchemy import func

import tmlib.models as tm
from tmlib.utils import notimplemented
from tmlib.readers import BFImageReader
from tmlib.readers import ImageReader
from tmlib.readers import JavaBridge
from tmlib.image import ChannelImage
from tmlib.workflow.api import ClusterRoutines
from tmlib.workflow import register_api

logger = logging.getLogger(__name__)


@register_api('imextract')
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
            # Group file mappings per site to ensure that all z-planes of
            # one site end up on the same machine.
            # They will be written into the same file and trying to access the
            # same file from different machines will create problems with file
            # locks.
            file_mappings_per_site = dict(session.query(
                    tm.ImageFileMapping.site_id,
                    func.array_agg(tm.ImageFileMapping.id)
                ).\
                join(tm.Channel).\
                filter(tm.Channel.experiment_id == self.experiment_id).\
                group_by(tm.ImageFileMapping.site_id).\
                all())
            batches = self._create_batches(
                file_mappings_per_site.values(), args.batch_size
            )
            for batch in batches:
                ids = list(np.array(batch).flat)
                fmappings = session.query(tm.ImageFileMapping).\
                    filter(tm.ImageFileMapping.id.in_(ids)).\
                    all()
                job_count += 1
                job_descriptions['run'].append({
                    'id': job_count,
                    'inputs': {
                        'microscope_image_files': [
                            [
                                os.path.join(
                                    fmap.acquisition.
                                    microscope_images_location,
                                    f
                                )
                                for f in fmap.map['files']
                            ]
                            for fmap in fmappings
                        ]
                    },
                    'outputs': {
                        'channel_image_files': [
                            os.path.join(
                                fmap.cycle.channel_images_location,
                                tm.ChannelImageFile.FILENAME_FORMAT.format(
                                    t=fmap.tpoint,
                                    w=fmap.site.well.name,
                                    y=fmap.site.y, x=fmap.site.x,
                                    c=fmap.wavelength
                                )
                            )
                            for fmap in fmappings
                        ]
                    },
                    'image_file_mapping_ids': ids
                })

            job_descriptions['collect'] = {'inputs': dict(), 'outputs': dict()}

        return job_descriptions

    def run_job(self, batch):
        '''Extracts individual planes from microscope image files and writes
        them into HDF5 files.

        Parameters
        ----------
        batch: dict
            job description
        '''
        file_mapping_ids = batch['image_file_mapping_ids']
        with tm.utils.Session() as session:
            fmappings = session.query(tm.ImageFileMapping.map).\
                filter(tm.ImageFileMapping.id.in_(file_mapping_ids)).\
                all()[0]
            series = np.array([m['series'] for m in fmappings]).flatten()
            planes = np.array([m['planes'] for m in fmappings]).flatten()
            if len(np.unique(series)) > 1 or len(np.unique(planes)) > 1:
                # Let's not use Java in case we don't have to!
                logger.debug('use BioFormats image reader')
                Reader = BFImageReader
                subset = True
            else:
                logger.debug('use standard image reader')
                Reader = ImageReader
                subset = False
            with JavaBridge(active=subset):
                for i, fid in enumerate(file_mapping_ids):
                    filenames = batch['inputs']['microscope_image_files'][i]
                    with tm.utils.Session() as session:
                        fmapping = session.query(tm.ImageFileMapping).get(fid)
                        planes = list()
                        for j, f in enumerate(filenames):
                            logger.info(
                                'extract image from file: %s',
                                os.path.basename(f)
                            )
                            plane_ix = fmapping.map['planes'][j]
                            series_ix = fmapping.map['series'][j]
                            with Reader(f) as reader:
                                if subset:
                                    p = reader.read_subset(
                                        plane=plane_ix, series=series_ix
                                    )
                                else:
                                    p = reader.read()
                            planes.append(p)

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
                            tpoint=fmapping.tpoint,
                            site_id=fmapping.site_id, cycle_id=fmapping.cycle_id,
                            channel_id=fmapping.channel_id
                        )
                        logger.info(
                            'store pixels plane #%d in image file: %s',
                            fmapping.zplane, image_file.name
                        )
                        image_file.put(img, z=fmapping.zplane)

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
