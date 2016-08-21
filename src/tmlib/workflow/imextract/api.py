import os
import numpy as np
import pandas as pd
import logging
import collections
from sqlalchemy import func

import tmlib.models as tm
from tmlib.models.utils import delete_location
from tmlib.utils import notimplemented
from tmlib.readers import BFImageReader
from tmlib.readers import ImageReader
from tmlib.readers import JavaBridge
from tmlib.image import ChannelImage
from tmlib.metadata import ChannelImageMetadata
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
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            # Group file mappings per site to ensure that all z-planes of
            # one site end up on the same machine.
            # They will be written into the same file and trying to access the
            # same file from different machines will create problems with file
            # locks.
            file_mappings_per_site = dict(
                session.query(
                    tm.ImageFileMapping.site_id,
                    func.array_agg(tm.ImageFileMapping.id)
                ).\
                group_by(tm.ImageFileMapping.site_id).\
                all()
            )
            batches = self._create_batches(
                file_mappings_per_site.values(), args.batch_size
            )
            for batch in batches:
                ids = list(np.array(batch).flat)
                fmappings = session.query(tm.ImageFileMapping).\
                    filter(tm.ImageFileMapping.id.in_(ids)).\
                    order_by(tm.ImageFileMapping.id).\
                    all()
                job_count += 1
                job_descriptions['run'].append({
                    'id': job_count,
                    'inputs': {
                        'microscope_image_files': [
                            [
                                os.path.join(
                                    fmap.acquisition.microscope_images_location,
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
                                    c=fmap.channel.index
                                )
                            )
                            for fmap in fmappings
                        ]
                    },
                    'image_file_mapping_ids': ids,
                    'mip': args.mip
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
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            fmappings = session.query(tm.ImageFileMapping.map).\
                filter(tm.ImageFileMapping.id.in_(file_mapping_ids)).\
                all()
            series = np.array([m[0]['series'] for m in fmappings]).flatten()
            planes = np.array([m[0]['planes'] for m in fmappings]).flatten()
            if len(np.unique(series)) > 1 or len(np.unique(planes)) > 1:
                # Let's not use Java in case we don't have to!
                logger.debug('use BioFormats image reader')
                Reader = BFImageReader
                subset = True
            else:
                logger.debug('use standard image reader')
                # Don't take the risk. Python-Bioformats may overcomplicate
                # things for this simple case.
                Reader = ImageReader
                subset = False
            with JavaBridge(active=subset):
                with tm.utils.ExperimentSession(self.experiment_id) as session:
                    for i, fid in enumerate(file_mapping_ids):
                        fmapping = session.query(tm.ImageFileMapping).get(fid)
                        planes = list()
                        for j, f in enumerate(fmapping.map['files']):
                            logger.info(
                                'extract pixel planes from file: %s', f
                            )
                            plane_ix = fmapping.map['planes'][j]
                            series_ix = fmapping.map['series'][j]
                            filename = os.path.join(
                                fmapping.acquisition.microscope_images_location,
                                f
                            )
                            with Reader(filename) as reader:
                                if subset:
                                    p = reader.read_subset(
                                        plane=plane_ix, series=series_ix
                                    )
                                else:
                                    p = reader.read()
                            planes.append(p)

                        dtype = planes[0].dtype
                        dims = planes[0].shape
                        stack = np.dstack(planes)
                        image_file = session.get_or_create(
                            tm.ChannelImageFile,
                            tpoint=fmapping.tpoint,
                            site_id=fmapping.site_id,
                            cycle_id=fmapping.cycle_id,
                            channel_id=fmapping.channel_id
                        )
                        metadata = ChannelImageMetadata(
                            channel_id=image_file.channel_id,
                            cycle_id=image_file.cycle_id,
                            site_id=image_file.site_id,
                            tpoint=image_file.tpoint
                        )
                        img = ChannelImage(stack, metadata)
                        if batch['mip']:
                            logger.info('perform intensity projection')
                            img = img.project()
                        logger.info('store image file: %s', image_file.name)
                        image_file.put(img)

    def delete_previous_job_output(self):
        '''Deletes all instances of class
        :py:class:`tm.ChannelImageFile` as well as all children for
        the processed experiment.
        '''
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            cycles = session.query(tm.Cycle).all()
            images_locations = [c.channel_images_location for c in cycles]
            logger.info('delete existing channel image files')
            session.drop_and_recreate(tm.ChannelImageFile)
        for loc in images_locations:
            delete_location(loc)

    def collect_job_output(self, batch):
        '''Omits channel image files that do not exist across all cycles.

        Parameters
        ----------
        batch: dict
            job description
        '''
        # TODO: this does not work for experiments with multiple plates
        # with tm.utils.Session() as session:
        #     metadata = pd.DataFrame(
        #         session.query(
        #             tm.ChannelImageFile.id,
        #             tm.ChannelImageFile.site_id,
        #             tm.ChannelImageFile.cycle_id,
        #             tm.Cycle.plate_id
        #         ).
        #         join(tm.Cycle).\
        #         join(tm.Plate).
        #         filter(tm.Plate.experiment_id == self.experiment_id).
        #         all()
        #     )
        #     cycle_ids = np.unique(metadata.cycle_id)
        #     site_group = metadata.groupby('site_id')
        #     for i, sg in site_group:
        #         # If files don't exist
        #         if (len(np.setdiff1d(cycle_ids, sg.cycle_id.values)) > 0 and
        #                 len(np.unique(sg.plate_id)) == 1):
        #             sites_to_omit = session.query(tm.ChannelImageFile).\
        #                 filter(tm.ChannelImageFile.id.in_(sg.id.values)).\
        #                 all()
        #             for site in sites_to_omit:
        #                 site.omitted = True
        #             session.add_all(sites_to_omit)
