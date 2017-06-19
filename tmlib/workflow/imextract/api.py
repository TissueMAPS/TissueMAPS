# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import os
import logging
import collections
import numpy as np
import pandas as pd
from sqlalchemy import func

import tmlib.models as tm
from tmlib.utils import notimplemented
from tmlib.readers import BFImageReader
from tmlib.readers import ImageReader
from tmlib.readers import JavaBridge
from tmlib.image import ChannelImage
from tmlib.metadata import ChannelImageMetadata
from tmlib.workflow.api import WorkflowStepAPI
from tmlib.workflow import register_step_api

logger = logging.getLogger(__name__)


@register_step_api('imextract')
class ImageExtractor(WorkflowStepAPI):

    '''Class for extraction of pixel arrays (planes) stored in image files using
    `python-bioformats <https://github.com/CellProfiler/python-bioformats>`_.

    '''

    def __init__(self, experiment_id):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of the processed experiment
        '''
        super(ImageExtractor, self).__init__(experiment_id)

    def create_run_batches(self, args):
        '''Creates job descriptions for parallel processing.

        Parameters
        ----------
        args: tmlib.workflow.imextract.args.ImextractBatchArguments
            step-specific arguments

        Returns
        -------
        generator
            job descriptions
        '''
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            channel_image_files = session.query(tm.ChannelImageFile.id).all()
            file_ids = [f.id for f in channel_image_files]
            batches = self._create_batches(file_ids, args.batch_size)
            for i, file_ids in enumerate(batches):
                yield {'id': i+1, 'channel_image_file_ids': file_ids}

    def create_collect_batch(self, args):
        '''Creates a job description for the *collect* phase.

        Parameters
        ----------
        args: tmlib.workflow.imextract.args.ImextractBatchArguments
            step-specific arguments

        Returns
        -------
        dict
            job description
        '''
        return {'delete': args.delete}

    def run_job(self, batch, assume_clean_state=False):
        '''Extracts individual planes from microscope image files and writes
        them into HDF5 files.

        Parameters
        ----------
        batch: dict
            job description
        assume_clean_state: bool, optional
            assume that output of previous runs has already been cleaned up
        '''
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            channel_image_file = session.query(tm.ChannelImageFile).\
                get(batch['channel_image_file_ids'][0])
            fmap = channel_image_file.file_map
            series = fmap['series']
            planes = fmap['planes']
            if len(np.unique(series)) > 1 or len(np.unique(planes)) > 1:
                logger.debug('use BioFormats image reader')
                Reader = BFImageReader
                subset = True
            else:
                # Let's not use Java in case we don't really have to!
                logger.debug('use standard image reader')
                Reader = ImageReader
                subset = False

        with JavaBridge(active=subset):
            with tm.utils.ExperimentSession(self.experiment_id) as session:
                acquisition_lut = {
                    a.id: a for a in session.query(tm.Acquisition).all()
                }
                for i, fid in enumerate(batch['channel_image_file_ids']):
                    logger.info(
                        'extract pixels for channel image file #%d', fid
                    )
                    image_file = session.query(tm.ChannelImageFile).get(fid)
                    planes = list()
                    fmap = image_file.file_map
                    for j, filename in enumerate(fmap['files']):
                        plane_ix = fmap['planes'][j]
                        series_ix = fmap['series'][j]
                        logger.debug(
                            'extract pixel plane #%d of series #%d from file: %s',
                            plane_ix, series_ix, filename
                        )
                        acquisition = acquisition_lut[image_file.acquisition_id]
                        filepath = os.path.join(
                            acquisition.microscope_images_location,
                            filename
                        )
                        with Reader(filepath) as reader:
                            if subset:
                                p = reader.read_subset(
                                    plane=plane_ix, series=series_ix
                                )
                            else:
                                p = reader.read()
                        planes.append(p)

                    if len(planes) > 1:
                        logger.info('perform maximumn intensity projection')
                        stack = np.dstack(planes)
                        pixel_array = np.max(stack, axis=2).astype(stack.dtype)
                    else:
                        pixel_array = planes[0]

                    img = ChannelImage(pixel_array)
                    logger.info('write pixels to file on disk')
                    image_file.put(img)

    def delete_previous_job_output(self):
        '''Deletes all instances of class
        :class:`ChannelImageFile <tmlib.models.file.ChannelImageFile>` as well
        as all children for the processed experiment.
        '''
        logger.info('delete existing channel image files')
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            channels = session.query(tm.Channel).all()
            for ch in channels:
                ch.remove_image_files()

    def collect_job_output(self, batch):
        '''Deletes all instances of
        :class:`MicroscopeImageFile <tmlib.models.file.MicroscopeImageFile>`
        in case
        :attr:`delete <tmlib.workflow.imextract.args.ImextractBatchArguments>`
        is set to ``True``.

        Parameters
        ----------
        batch: dict
            job description

        Note
        ----
        Files are only deleted after individual planes have been extracted,
        because it may lead to problems depending on how planes are distributed
        across individual microscope image files.
        '''
        if batch['delete']:
            logger.info('delete all microscope image files')
            with tm.utils.ExperimentSession(self.experiment_id) as session:
                session.query(tm.MicroscopeImageFile).delete()
