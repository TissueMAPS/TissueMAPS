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
import numpy as np
import collections
import itertools
import shapely.geometry
import psycopg2
import sqlalchemy.orm
from sqlalchemy import func
from sqlalchemy.orm.exc import NoResultFound
from gc3libs.quantity import Duration
from gc3libs.quantity import Memory

import tmlib.models as tm
from tmlib.utils import flatten, notimplemented, create_partitions
from tmlib.image import PyramidTile
from tmlib.image import Image
from tmlib.errors import DataIntegrityError
from tmlib.errors import WorkflowError
from tmlib.models.utils import delete_location
from tmlib.workflow.api import WorkflowStepAPI
from tmlib.workflow.jobs import RunJob
from tmlib.workflow.jobs import SingleRunPhase
from tmlib.workflow.jobs import MultiRunPhase
from tmlib.workflow.jobs import CollectJob
from tmlib.workflow import register_step_api

logger = logging.getLogger(__name__)


@register_step_api('illuminati')
class PyramidBuilder(WorkflowStepAPI):

    def __init__(self, experiment_id):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of the processed experiment
        '''
        super(PyramidBuilder, self).__init__(experiment_id)

    def create_run_batches(self, args):
        '''Creates job descriptions for parallel computing.

        Parameters
        ----------
        args: tmlib.workflow.illuminati.args.IlluminatiBatchArguments
            step-specific arguments

        Returns
        -------
        generator
            job descriptions
        '''
        logger.info('performing data integrity tests')
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            n_images_per_site = session.query(
                    func.count(tm.ChannelImageFile.id)
                ).\
                group_by(tm.ChannelImageFile.site_id).\
                all()
            if len(set(n_images_per_site)) > 1:
                raise DataIntegrityError(
                    'Number of channel image files must be the same for '
                    'each site!'
                )
            n_wells_per_plate = session.query(func.count(tm.Well.id)).\
                group_by(tm.Well.plate_id).\
                all()
            # TODO: is this restraint still required?
            if len(set(n_wells_per_plate)) > 1:
                raise DataIntegrityError(
                    'Number of wells must be the same for each plate!'
                )

        logger.info('create job descriptions')
        logger.debug('create descriptions for "run" jobs')
        job_count = 0
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            experiment = session.query(tm.Experiment).one()
            count = 0
            for channel in session.query(tm.Channel.id).distinct():
                logger.info('create layers for channel %d', channel.id)
                results = session.query(tm.ChannelImageFile.zplane).\
                    filter_by(channel_id=channel.id).\
                    distinct()
                zplanes = [r.zplane for r in results]
                results = session.query(tm.ChannelImageFile.tpoint).\
                    filter_by(channel_id=channel.id).\
                    distinct()
                tpoints = [r.tpoint for r in results]
                for t, z in itertools.product(tpoints, zplanes):
                    logger.info('create layer for tpoint %d, zplane %d', t, z)
                    image_files = session.query(tm.ChannelImageFile.id).\
                        filter_by(channel_id=channel.id, tpoint=t, zplane=z).\
                        order_by(tm.ChannelImageFile.site_id).\
                        all()
                    image_file_ids = [f.id for f in image_files]
                    layer = session.get_or_create(
                        tm.ChannelLayer, channel_id=channel.id,
                        tpoint=t, zplane=z
                    )

                    if args.clip:
                        logger.info('clip intensities')
                        # Illumination statistics may not have been calculated
                        # and are not required in case a clip value is provided.
                        if args.clip_value is None:
                            logger.info(
                                'calculate clip value at percentile %d',
                                args.clip_percent
                            )
                            try:
                                stats_file = session.query(tm.IllumstatsFile).\
                                    filter_by(channel_id=layer.channel_id).\
                                    one()
                            except NoResultFound:
                                raise WorkflowError(
                                    'No illumination statistics file found '
                                    'for channel %d' % layer.channel_id
                                )
                            stats = stats_file.get()
                            clip_max = stats.get_closest_percentile(
                                args.clip_percent
                            )
                            # If pixel values are too low for the channel,
                            # the channel is probably "empty"
                            # (for example because the staining didn't work).
                            # In this case we want to prevent that too extreme
                            # rescaling is applied, which would look shitty.
                            # The choice of the threshold level is arbitrary.
                            clip_min = stats.get_closest_percentile(0.001)
                            if layer.channel.bit_depth == 8:
                                if clip_max < 255:
                                    clip_max = 255
                                    
                            else:
                                if clip_max < clip_min + 255:
                                    clip_max = clip_min + 255
                            logger.info('clip value: %d', clip_max)
                        else:
                            logger.info('use provided clip value')
                            clip_max = args.clip_value
                            logger.info('clip value: %d', clip_max)
                            clip_min = stats.get_closest_percentile(0.001)
                    else:
                        logger.debug('don\'t clip intensities')
                        clip_max = 2**layer.channel.bit_depth - 1
                        clip_min = 0

                    layer.max_intensity = clip_max
                    layer.min_intensity = clip_min

                    if count == 0:
                        logger.info('calculate size of pyramid base level')
                        h, w = layer.calculate_max_image_size()
                        d = layer.calculate_zoom_levels(h, w)
                        experiment.pyramid_depth = d
                        experiment.pyramid_height = h
                        experiment.pyramid_width = w
                    count += 1
                    n_levels = experiment.pyramid_depth
                    max_zoomlevel_index = n_levels - 1
                    for index, level in enumerate(reversed(range(n_levels))):
                        logger.info('create batches for pyramid level %d', level)
                        # The layer "level" increases from top to bottom.
                        # We build the layer bottom-up, therefore, the "index"
                        # decreases from top to bottom.
                        if level == max_zoomlevel_index:
                            # For the base level, batches are composed of
                            # image files, which will get chopped into tiles.
                            batch_size = args.batch_size
                            batches = self._create_batches(
                                image_file_ids, batch_size
                            )
                        else:
                            # For the subsequent levels, batches are composed of
                            # tiles of the previous, next higher level.
                            # Therefore, the batch size needs to be adjusted.
                            if index == 1:
                                batch_size *= 25
                            else:
                                batch_size /= 4
                            batches = self._create_batches(
                                np.arange(np.prod(layer.dimensions[level])),
                                batch_size
                            )

                        for batch in batches:
                            job_count += 1
                            # For the highest resolution level, the inputs
                            # are channel image files. For all other levels,
                            # the inputs are the tiles of the next higher
                            # resolution level.
                            if level == max_zoomlevel_index:
                                yield {
                                    'id': job_count,
                                    'outputs': {},
                                    'layer_id': layer.id,
                                    'level': level,
                                    'index': index,
                                    'image_file_ids': batch,
                                    'align': args.align,
                                    'illumcorr': args.illumcorr
                                }
                            else:
                                rows = np.arange(layer.dimensions[level][0])
                                cols = np.arange(layer.dimensions[level][1])
                                coordinates = np.array(
                                    list(itertools.product(rows, cols))
                                )[batch].tolist()
                                yield {
                                    'id': job_count,
                                    'layer_id': layer.id,
                                    'level': level,
                                    'index': index,
                                    'coordinates': coordinates
                                }

    def delete_previous_job_output(self):
        '''Deletes all instances of
        :class:`ChannelLayer <tmlib.models.layer.ChannelLayer>` and
        :class:`ChannelLayerTile <tmlib.models.tile.ChannelLayerTile>` as well
        as instances of
        :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`,
        :class:`Mapobject <tmlib.models.mapobject.Mapobject>` and
        :class:`MapobjectSegmentation <tmlib.models.mapobject.MapobjectSegmentation>`
        for each :class:`Plate <tmlib.models.plate.Plate>`,
        :class:`Well <tmlib.models.well.Well>` and
        :class:`Site <tmlib.models.site.Site>`.
        '''
        with tm.utils.ExperimentSession(self.experiment_id, False) as session:
            logger.info('delete existing channel layers')
            session.query(tm.ChannelLayerTile).delete()
            session.query(tm.ChannelLayer).delete()
            logger.info('delete existing static mapobject types')
            session.query(tm.Mapobject).delete()
            session.query(tm.MapobjectType).delete()

    def create_run_phase(self, submission_id, parent_id):
        '''Creates a job collection for the "run" phase of the step.

        Parameters
        ----------
        submission_id: int
            ID of the corresponding
            :class:`Submission <tmlib.models.submission.Submission>`
        parent_id: int
            ID of the parent
            :class:`WorkflowStep <tmlib.workflow.workflow.WorkflowStep>`

        Returns
        -------
        tmlib.workflow.job.MultiRunPhase
            collection of "run" jobs
        '''
        return MultiRunPhase(
            step_name=self.step_name, submission_id=submission_id,
            parent_id=parent_id
        )

    def create_run_jobs(self, user_name, job_collection,
            verbosity, duration, memory, cores):
        '''Creates jobs for the parallel "run" phase of the step.
        The `illuminati` step is special in the sense that it implements
        multiple sequential runs within the "run" phase to build one pyramid
        zoom level after another.

        Parameters
        ----------
        user_name: str
            name of the submitting user
        job_collection: tmlib.workflow.jobs.RunPhase
            emtpy collection for "run" jobs
        verbosity: int
            logging verbosity for jobs
        duration: str
            computational time that should be allocated for a single job;
            in HH:MM:SS format
        memory: int
            amount of memory in Megabyte that should be allocated for a single
        cores: int
            number of CPU cores that should be allocated for a single job

        Returns
        -------
        tmlib.workflow.jobs.RunPhase
            collection of jobs
        '''
        logger.info(
            'create "run" jobs for submission %d', job_collection.submission_id
        )
        logger.debug('allocated time for "run" jobs: %s', duration)
        logger.debug('allocated memory for "run" jobs: %d MB', memory)
        logger.debug('allocated cores for "run" jobs: %d', cores)

        multi_run_jobs = collections.defaultdict(list)
        job_ids = self.get_run_job_ids()
        for j in job_ids:
            batch = self.get_run_batch(j)
            multi_run_jobs[batch['index']].append(j)

        for index, job_ids in multi_run_jobs.iteritems():
            subjob_collection = SingleRunPhase(
                step_name=self.step_name,
                index=index,
                submission_id=job_collection.submission_id,
                parent_id=job_collection.persistent_id
            )

            for j in job_ids:
                job = RunJob(
                    step_name=self.step_name,
                    arguments=self._build_run_command(j, verbosity),
                    output_dir=self.log_location,
                    job_id=j,
                    index=index,
                    submission_id=subjob_collection.submission_id,
                    parent_id=subjob_collection.persistent_id,
                    user_name=user_name
                )
                if duration:
                    job.requested_walltime = Duration(duration)
                if memory:
                    job.requested_memory = Memory(memory, Memory.MB)
                if cores:
                    if not isinstance(cores, int):
                        raise TypeError(
                            'Argument "cores" must have type int.'
                        )
                    if not cores > 0:
                        raise ValueError(
                            'The value of "cores" must be positive.'
                        )
                    job.requested_cores = cores
                subjob_collection.add(job)
            job_collection.add(subjob_collection)

        return job_collection

    def _create_maxzoom_level_tiles(self, batch, assume_clean_state):
        exp_id = self.experiment_id
        with tm.utils.ExperimentSession(exp_id, transaction=False) as session:
            layer = session.query(tm.ChannelLayer).get(batch['layer_id'])
            logger.info(
                'process layer: channel=%s, zplane=%d, tpoint=%d',
                layer.channel.name, layer.zplane, layer.tpoint
            )
            logger.info('create tiles at zoom level %d', batch['level'])

            if batch['illumcorr']:
                logger.info('correct images for illumination artifacts')
                try:
                    logger.debug('load illumination statistics')
                    image_file = session.query(tm.ChannelImageFile).get(
                        batch['image_file_ids'][0]
                    )
                    stats_file = session.query(tm.IllumstatsFile).\
                        filter_by(channel_id=layer.channel_id).\
                        one()
                except NoResultFound:
                    raise WorkflowError(
                        'No illumination statistics file found for channel %d'
                        % layer.channel_id
                    )
                stats = stats_file.get()
            else:
                stats = None

            if batch['align']:
                logger.info('align images between cycles')

            clip_min = layer.min_intensity
            clip_max = layer.max_intensity

            for fid in batch['image_file_ids']:
                file = session.query(tm.ChannelImageFile).get(fid)
                logger.info('process image %d', file.id)
                tiles = layer.map_image_to_base_tiles(file)
                image_store = dict()
                image = file.get()
                if batch['illumcorr']:
                    logger.debug('correct image')
                    image = image.correct(stats)
                if batch['align']:
                    logger.debug('align image')
                    image = image.align(crop=False)
                if not image.is_uint8:
                    image = image.clip(clip_min, clip_max)
                    image = image.scale(clip_min, clip_max)
                image_store[file.id] = image

                extra_file_map = layer.map_base_tile_to_images(file.site)
                for t in tiles:
                    level = batch['level']
                    row = t['y']
                    column = t['x']
                    logger.debug(
                        'create tile: z=%d, y=%d, x=%d', level, row, column
                    )
                    tile = layer.extract_tile_from_image(
                        image_store[file.id], t['y_offset'], t['x_offset']
                    )

                    # Determine files that contain overlapping pixels,
                    # i.e. pixels falling into the currently processed tile
                    # that are not contained by the file.
                    file_coordinate = np.array((file.site.y, file.site.x))
                    extra_file_ids = extra_file_map[row, column]
                    if len(extra_file_ids) > 0:
                        logger.debug('tile overlaps multiple images')
                    for efid in extra_file_ids:
                        extra_file = session.query(tm.ChannelImageFile).\
                            get(efid)
                        if extra_file.id not in image_store:
                            image = extra_file.get()
                            if batch['illumcorr']:
                                logger.debug('correct image')
                                image = image.correct(stats)
                            if batch['align']:
                                logger.debug('align image')
                                image = image.align(crop=False)
                            if not image.is_uint8:
                                image = image.clip(clip_min, clip_max)
                                image = image.scale(clip_min, clip_max)
                            image_store[extra_file.id] = image

                        extra_file_coordinate = np.array((
                            extra_file.site.y, extra_file.site.x
                        ))

                        condition = file_coordinate > extra_file_coordinate
                        pixels = image_store[extra_file.id]
                        if all(condition):
                            logger.debug('insert pixels from top left image')
                            y = file.site.image_size[0] - abs(t['y_offset'])
                            x = file.site.image_size[1] - abs(t['x_offset'])
                            height = abs(t['y_offset'])
                            width = abs(t['x_offset'])
                            subtile = PyramidTile(
                                pixels.extract(y, height, x, width).array
                            )
                            tile.insert(subtile, 0, 0)
                        elif condition[0] and not condition[1]:
                            logger.debug('insert pixels from top image')
                            y = file.site.image_size[0] - abs(t['y_offset'])
                            height = abs(t['y_offset'])
                            if t['x_offset'] < 0:
                                x = 0
                                width = tile.dimensions[1] - abs(t['x_offset'])
                                x_offset = abs(t['x_offset'])
                            else:
                                x = t['x_offset']
                                width = tile.dimensions[1]
                                x_offset = 0
                            subtile = PyramidTile(
                                pixels.extract(y, height, x, width).array
                            )
                            tile.insert(subtile, 0, x_offset)
                        elif not condition[0] and condition[1]:
                            logger.debug('insert pixels from left image')
                            x = file.site.image_size[1] - abs(t['x_offset'])
                            width = abs(t['x_offset'])
                            if t['y_offset'] < 0:
                                y = 0
                                height = tile.dimensions[0] - abs(t['y_offset'])
                                y_offset = abs(t['y_offset'])
                            else:
                                y = t['y_offset']
                                height = tile.dimensions[0]
                                y_offset = 0
                            subtile = PyramidTile(
                                pixels.extract(y, height, x, width).array
                            )
                            tile.insert(subtile, y_offset, 0)
                        else:
                            raise IndexError(
                                'Tile shouldn\'t be in this batch!'
                            )

                    channel_layer_tile = tm.ChannelLayerTile(
                        channel_layer_id=layer.id,
                        z=level, y=row, x=column, pixels=tile
                    )
                    session.add(channel_layer_tile)


    def _create_lower_zoom_level_tiles(self, batch, assume_clean_state):
        exp_id = self.experiment_id
        with tm.utils.ExperimentSession(exp_id, transaction=False) as session:
            layer = session.query(tm.ChannelLayer).get(batch['layer_id'])
            logger.info('processing layer for channel %s', layer.channel.name)
            level = batch['level']
            logger.info('creating tiles at zoom level %d', batch['level'])
            layer_id = layer.id
            zoom_factor = layer.zoom_factor

            for coordinates in batch['coordinates']:
                row = coordinates[0]
                column = coordinates[1]
                pre_coordinates = layer.calc_coordinates_of_next_higher_level(
                    level, row, column
                )
                logger.debug(
                    'creating tile: z=%d, y=%d, x=%d', level, row, column
                )
                # Build the mosaic by loading required higher level tiles
                # (created in a previous run) and stitching them together
                pre_rows = np.unique([c[0] for c in pre_coordinates])
                pre_cols = np.unique([c[1] for c in pre_coordinates])
                for i, r in enumerate(pre_rows):
                    for j, c in enumerate(pre_cols):
                        pre_tile = session.query(tm.ChannelLayerTile).\
                            filter_by(
                                channel_layer_id=layer_id, z=level+1, y=r, x=c
                            ).\
                            one_or_none()
                        if pre_tile is not None:
                            pre_tile = pre_tile.pixels
                        else:
                            # Tiles at maxzoom level might not exist in
                            # case they did not fall into a region of
                            # the map occupied by an image.
                            # They must exist at the lower zoom levels,
                            # though, for subsampling.
                            if batch['index'] > 1:
                                raise ValueError(
                                    'Tile "%d-%d-%d" was not created.'
                                    % (level+1, r, c)
                                )
                            logger.debug(
                                'tile "%d-%d-%d" missing',
                                 batch['level']+1, r, c
                            )
                            pre_tile = PyramidTile.create_as_background()
                        # We have to temporally treat it as an "image",
                        # since a tile can per definition not be larger
                        # than 256x256 pixels.
                        # FIXME: This can be done more efficiently using
                        # a predefined array instead of these loops.
                        img = Image(pre_tile.array)
                        if j == 0:
                            row_img = img
                        else:
                            row_img = row_img.join(img, 'x')
                    if i == 0:
                        mosaic_img = row_img
                    else:
                        mosaic_img = mosaic_img.join(row_img, 'y')
                # Create the tile at the current level by downsampling
                # the mosaic image, which is composed of the 4 tiles
                # of the next higher zoom level
                tile = PyramidTile(mosaic_img.shrink(zoom_factor).array)
                channel_layer_tile = tm.ChannelLayerTile(
                    channel_layer_id=layer_id,
                    z=level, y=row, x=column, pixels=tile
                )
                session.add(channel_layer_tile)

    def run_job(self, batch, assume_clean_state=False):
        '''Creates 8-bit grayscale JPEG layer tiles.

        Parameters
        ----------
        batch: dict
            batches element
        assume_clean_state: bool, optional
            assume that output of previous runs has already been cleaned up
        '''
        if batch['index'] == 0:
            self._create_maxzoom_level_tiles(batch, assume_clean_state)
        else:
            self._create_lower_zoom_level_tiles(batch, assume_clean_state)

    def collect_job_output(self, batch):
        '''Creates :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`
        instances for :class:`Site <tmlib.models.site.Site>`,
        :class:`Well <tmlib.models.well.Well>`,
        and :class:`Plate <tmlib.models.plate.Plate>` types and creates for each
        object of these classes an instance of
        :class:`Mapobject <tmlib.models.mapobject.Mapobject>` and
        :class:`MapobjectSegmentation <tmlib.models.mapobject.MapobjectSegmentation>`.
        This allows visualizing these objects on the map and using them
        for efficient spatial queries.

        Parameters
        ----------
        batch: dict
            job description
        '''
        mapobject_mappings = {
            'Plates': tm.Plate, 'Wells': tm.Well, 'Sites': tm.Site
        }
        for name, cls in mapobject_mappings.iteritems():
            with tm.utils.ExperimentSession(self.experiment_id, transaction=False) as session:
                logger.info(
                    'create static mapobject type "%s" for reference type "%s"',
                    name, cls.__name__
                )
                mapobject_type = session.get_or_create(
                    tm.MapobjectType, name=name,
                    experiment_id=self.experiment_id, ref_type=cls.__name__
                )
                mapobject_type_id = mapobject_type.id
                segmentation_layer = session.get_or_create(
                    tm.SegmentationLayer, mapobject_type_id=mapobject_type_id
                )

                logger.info('create individual mapobjects of type "%s"', name)
                segmentations = dict()
                for obj in session.query(cls):
                    logger.debug(
                        'create mapobject for reference object #%d', obj.id
                    )
                    if name == 'Sites':
                        # We need to account for the "multiplexing" edge case.
                        offset = obj.aligned_offset
                        image_size = obj.aligned_image_size
                    else:
                        offset = obj.offset
                        image_size = obj.image_size
                    # First element: x axis
                    # Second element: inverted (!) y axis
                    # We further subtract one pixel such that the polygon
                    # defines the exact boundary of the objects. This is
                    # crucial for testing whether other objects intersect with
                    # the border.
                    ul = (offset[1] + 1, -1 * (offset[0] + 1))
                    ll = (ul[0], ul[1] - (image_size[0] - 3))
                    ur = (ul[0] + image_size[1] - 3, ul[1])
                    lr = (ll[0] + image_size[1] - 3, ll[1])
                    # Closed circle with coordinates sorted counter-clockwise
                    contour = np.array([ur, ul, ll, lr, ur])
                    polygon = shapely.geometry.Polygon(contour)
                    segmentations[obj.id] = {
                        'segmentation_layer_id': segmentation_layer.id,
                        'polygon': polygon
                    }

                logger.debug('delete existing mapobjects of type "%s"', name)
                session.query(tm.Mapobject).\
                    filter_by(mapobject_type_id=mapobject_type_id).\
                    delete()
                logger.debug('add new mapobjects of type "%s"', name)
                for key, value in segmentations.iteritems():
                    mapobject = tm.Mapobject(
                        partition_key=key, mapobject_type_id=mapobject_type_id
                    )
                    session.add(mapobject)
                    session.flush()
                    logger.debug('add mapobject #%d', mapobject.id)
                    mapobject_segmentation = tm.MapobjectSegmentation(
                        partition_key=key, mapobject_id=mapobject.id,
                        geom_polygon=value['polygon'],
                        geom_centroid=value['polygon'].centroid,
                        segmentation_layer_id=value['segmentation_layer_id'],
                    )
                    session.add(mapobject_segmentation)
