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
from tmlib.utils import flatten, notimplemented
from tmlib.image import PyramidTile
from tmlib.image import Image
from tmlib.errors import DataIntegrityError
from tmlib.errors import WorkflowError
from tmlib.models.utils import delete_location
from tmlib.workflow.api import ClusterRoutines
from tmlib.workflow.jobs import RunJob
from tmlib.workflow.jobs import SingleRunJobCollection
from tmlib.workflow.jobs import MultiRunJobCollection
from tmlib.workflow.jobs import CollectJob
from tmlib.workflow import register_step_api

logger = logging.getLogger(__name__)


@register_step_api('illuminati')
class PyramidBuilder(ClusterRoutines):

    def __init__(self, experiment_id, verbosity):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of the processed experiment
        verbosity: int
            logging level
        '''
        super(PyramidBuilder, self).__init__(experiment_id, verbosity)

    def list_input_files(self, batches):
        '''Provides a list of all input files that are required by the step.

        Parameters
        ----------
        batches: List[dict]
            job descriptions
        '''
        files = list()
        if batches['run']:
            run_files = flatten([
                self._make_paths_absolute(j)['inputs'].values()
                for j in batches['run']
                if j['index'] == 0  # only base tile inputs
            ])
            if all([isinstance(f, list) for f in run_files]):
                run_files = flatten(run_files)
                if all([isinstance(f, list) for f in run_files]):
                    run_files = flatten(run_files)
                files.extend(run_files)
            elif any([isinstance(f, dict) for f in run_files]):
                files.extend(
                    flatten([
                        flatten(f.values())
                        for f in run_files if isinstance(f, dict)
                    ])
                )
            else:
                files.extend(run_files)
        return files

    def create_batches(self, args):
        '''Creates job descriptions for parallel computing.

        Parameters
        ----------
        args: tmlib.illuminati.args.IlluminatiInitArgs
            step-specific arguments

        Returns
        -------
        Dict[str, List[dict] or dict]
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
                    'The number of channel image files must be the same for '
                    'each site!'
                )
            n_wells_per_plate = session.query(func.count(tm.Well.id)).\
                group_by(tm.Well.plate_id).\
                all()
            # TODO: is this restraint still required?
            if len(set(n_wells_per_plate)) > 1:
                raise DataIntegrityError(
                    'The number of wells must be the same for each plate!'
                )

        logger.info('create job descriptions')
        logger.debug('create descriptions for "run" jobs')
        job_descriptions = dict()
        job_descriptions['run'] = list()
        job_count = 0
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            experiment = session.query(tm.Experiment).one()
            count = 0
            for cid in session.query(tm.Channel.id).distinct():

                n_zplanes = session.query(tm.ChannelImageFile.n_planes).\
                    filter_by(channel_id=cid).\
                    first()[0]
                zplanes = range(n_zplanes)

                tpoints = session.query(tm.ChannelImageFile.tpoint).\
                    filter_by(channel_id=cid).\
                    distinct()

                for t, z in itertools.product(tpoints, zplanes):
                    image_files = session.query(tm.ChannelImageFile).\
                        filter_by(channel_id=cid, tpoint=t).\
                        order_by(tm.ChannelImageFile.site_id).\
                        all()

                    layer = session.get_or_create(
                        tm.ChannelLayer, channel_id=cid, tpoint=t, zplane=z
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
                                illumstats_file = session.query(tm.IllumstatsFile).\
                                    filter_by(channel_id=layer.channel_id).\
                                    one()
                            except NoResultFound:
                                raise WorkflowError(
                                    'No illumination statistics file found '
                                    'for channel %d' % layer.channel_id
                                )
                            stats = illumstats_file.get()
                            clip_max = stats.get_closest_percentile(
                                args.clip_percent
                            )
                            # If pixel values are too low for the channel,
                            # the channel is probably "empty"
                            # (for example because the staining didn't work).
                            # In this case we want to prevent that too extreme
                            # rescaling is applied, which would look shitty.
                            # The choice of the threshold level is arbitrary.
                            if clip_max < 500:
                                clip_max = 500
                            logger.info('clip value: %d', clip_max)
                            clip_min = stats.get_closest_percentile(0.001)
                        else:
                            logger.info('use provided clip value')
                            clip_max = args.clip_value
                            logger.info('clip value: %d', clip_max)
                            clip_min = 0
                    else:
                        logger.debug('don\'t clip intensities')
                        clip_max = 2**layer.channel.bit_depth - 1
                        clip_min = 0

                    layer.max_intensity = clip_max
                    layer.min_intensity = clip_min

                    if count == 0:
                        h, w = layer.calculate_max_image_size()
                        d = layer.calculate_zoom_levels(h, w)
                        experiment.pyramid_depth = d
                        experiment.pyramid_height = h
                        experiment.pyramid_width = w
                    count += 1
                    n_levels = experiment.pyramid_depth
                    max_zoomlevel_index = n_levels - 1
                    for index, level in enumerate(reversed(range(n_levels))):
                        logger.debug('pyramid level %d', level)
                        # The layer "level" increases from top to bottom.
                        # We build the layer bottom-up, therefore, the "index"
                        # decreases from top to bottom.
                        if level == max_zoomlevel_index:
                            # For the base level, batches are composed of
                            # image files, which will get chopped into tiles.
                            batch_size = args.batch_size
                            batches = self._create_batches(
                                np.arange(len(image_files)), batch_size
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
                                image_file_subset = np.array(image_files)[batch]
                                input_files = list()
                                image_file_ids = list()
                                for f in image_file_subset:
                                    input_files.append(f.location)
                                    image_file_ids.append(f.id)
                                description = {
                                    'id': job_count,
                                    'inputs': {'image_files': input_files},
                                    'outputs': {},
                                    'layer_id': layer.id,
                                    'level': level,
                                    'index': index,
                                    'image_file_ids': image_file_ids,
                                    'align': args.align,
                                    'illumcorr': args.illumcorr
                                }
                            else:
                                rows = np.arange(layer.dimensions[level][0])
                                cols = np.arange(layer.dimensions[level][1])
                                coordinates = np.array(
                                    list(itertools.product(rows, cols))
                                )[batch].tolist()
                                description = {
                                    'id': job_count,
                                    'inputs': {},
                                    'outputs': {},
                                    'layer_id': layer.id,
                                    'level': level,
                                    'index': index,
                                    'coordinates': coordinates
                                }

                            job_descriptions['run'].append(description)

        job_descriptions['collect'] = {'inputs': {}, 'outputs': {}}
        return job_descriptions

    def delete_previous_job_output(self):
        '''Deletes all instances of
        :class:`ChannelLayer <tmlib.models.layer.ChannelLayer>` and
        :class:`ChannelLayerTile <tmlib.models.tile.ChannelLayerTile>`.
        '''
        with tm.utils.ExperimentConnection(self.experiment_id) as connection:
            logger.info('delete existing channel layers')
            tm.ChannelLayer.delete_cascade(connection)
            logger.info('delete existing static mapobject types')
            tm.MapobjectType.delete_cascade(
                connection, ref_type=tm.Plate.__name__
            )
            tm.MapobjectType.delete_cascade(
                connection, ref_type=tm.Well.__name__
            )
            tm.MapobjectType.delete_cascade(
                connection, ref_type=tm.Site.__name__
            )

    def create_run_job_collection(self, submission_id):
        '''tmlib.workflow.job.MultiRunJobCollection: collection of "run" jobs
        '''
        return MultiRunJobCollection(
            step_name=self.step_name, submission_id=submission_id
        )

    def create_run_jobs(self, submission_id, user_name, job_collection, batches,
            duration, memory, cores):
        '''Creates jobs for the parallel "run" phase of the step.
        The `illuminati` step is special in the sense that it implements
        a mutliple sequential runs with the "run" phase.

        Parameters
        ----------
        submission_id: int
            ID of the corresponding submission
        user_name: str
            name of the submitting user
        job_collection: tmlib.workflow.jobs.MultiRunJobCollection
            emtpy collection for "run" jobs
        batches: List[dict]
            job descriptions
        duration: str
            computational time that should be allocated for a single job;
            in HH:MM:SS format
        memory: int
            amount of memory in Megabyte that should be allocated for a single
        cores: int
            number of CPU cores that should be allocated for a single job

        Returns
        -------
        tmlib.workflow.jobs.MultipleRunJobCollection
            run jobs
        '''
        logger.info('create "run" jobs for submission %d', submission_id)
        logger.debug('allocated time for "run" jobs: %s', duration)
        logger.debug('allocated memory for "run" jobs: %d MB', memory)
        logger.debug('allocated cores for "run" jobs: %d', cores)

        multi_run_jobs = collections.defaultdict(list)
        for b in batches:
            job = RunJob(
                step_name=self.step_name,
                arguments=self._build_run_command(b['id']),
                output_dir=self.log_location,
                job_id=b['id'],
                index=b['index'],
                submission_id=submission_id,
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
            multi_run_jobs[b['index']].append(job)

        for index, jobs in multi_run_jobs.iteritems():
            job_collection.add(
                SingleRunJobCollection(
                    step_name=self.step_name,
                    jobs=jobs,
                    index=index,
                    submission_id=submission_id
                )
            )

        return job_collection

    def _create_maxzoom_level_tiles(self, batch):
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            layer = session.query(tm.ChannelLayer).get(batch['layer_id'])
            logger.info(
                'process layer: channel=%d, zplane=%d, tpoint=%d',
                layer.channel.index, layer.zplane, layer.tpoint
            )
            logger.info(
                'create non-empty tiles at maximum zoom level %d',
                batch['level']
            )

            if batch['illumcorr']:
                logger.info('correct images for illumination artifacts')
                try:
                    logger.debug('load illumination statistics')
                    illumstats_file = session.query(tm.IllumstatsFile).\
                        filter_by(
                            channel_id=layer.channel_id,
                            cycle_id=layer.channel.image_files[0].cycle_id
                        ).\
                        one()
                except NoResultFound:
                    raise WorkflowError(
                        'No illumination statistics file found for channel %d'
                        % layer.channel_id
                    )
                stats = illumstats_file.get()
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
                image = file.get(z=layer.zplane)
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
                            image = extra_file.get(z=layer.zplane)
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

                    with tm.utils.ExperimentConnection(self.experiment_id) as conn:
                        tm.ChannelLayerTile.add(
                            conn, channel_layer_id=layer.id,
                            z=level, y=row, x=column, tile=tile
                        )

    def _create_lower_zoom_level_tiles(self, batch):
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            layer = session.query(tm.ChannelLayer).get(batch['layer_id'])
            logger.info('processing layer: channel %d', layer.channel.index)
            level = batch['level']
            logger.info('creating tiles at zoom level %d', batch['level'])
            layer_id = layer.id
            zoom_factor = layer.zoom_factor

            for current_coordinate in batch['coordinates']:
                row, column = tuple(current_coordinate)
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
                with tm.utils.ExperimentConnection(self.experiment_id) as conn:
                    for i, r in enumerate(pre_rows):
                        for j, c in enumerate(pre_cols):
                            conn.execute('''
                                SELECT pixels FROM channel_layer_tiles
                                WHERE channel_layer_id=%(channel_layer_id)s
                                AND z=%(z)s AND y=%(y)s AND x=%(x)s;
                            ''', {
                                'z': level+1, 'y': r, 'x': c,
                                'channel_layer_id': layer_id
                            })
                            pre_tile = conn.fetchone()
                            if pre_tile:
                                pre_tile = PyramidTile.create_from_buffer(
                                    pre_tile.pixels
                                )
                            else:
                                # Tiles at maxzoom level might not exist in case
                                # they are empty. They must exist at the lower
                                # levels however.
                                if batch['index'] > 1:
                                    raise ValueError(
                                        'Tile "%d-%d-%d" was not created.'
                                        % (level+1, r, c)
                                    )
                                logger.debug(
                                    'tile "%d-%d-%d" missing - might be empty',
                                     batch['level']+1, r, c
                                )
                                pre_tile = PyramidTile.create_as_background()
                            # We have to temporally treat it as an "image",
                            # since a tile can per definition not be larger
                            # than 256x256 pixels.
                            img = Image(pre_tile.array)
                            if j == 0:
                                row_img = img
                            else:
                                row_img = row_img.join(img, 'x')
                        if i == 0:
                            mosaic_img = row_img
                        else:
                            mosaic_img = mosaic_img.join(row_img, 'y')
                    # Create the tile at the current level by downsampling the
                    # mosaic image, which is composed of the 4 tiles of the next
                    # higher zoom level
                    tile = PyramidTile(mosaic_img.shrink(zoom_factor).array)
                    tm.ChannelLayerTile.add(
                        conn, channel_layer_id=layer_id,
                        z=level, y=row, x=column, tile=tile
                    )

    def run_job(self, batch):
        '''Creates 8-bit grayscale JPEG layer tiles.

        Parameters
        ----------
        batch: dict
            batches element
        '''
        if batch['index'] == 0:
            self._create_maxzoom_level_tiles(batch)
        else:
            self._create_lower_zoom_level_tiles(batch)

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
            with tm.utils.ExperimentSession(self.experiment_id) as session:
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
                    # First element: x axis
                    # Second element: inverted (!) y axis
                    ul = (obj.offset[1], -1 * obj.offset[0])
                    ll = (ul[0] + obj.image_size[1], ul[1])
                    ur = (ul[0], ul[1] - obj.image_size[0])
                    lr = (ll[0], ul[1] - obj.image_size[0])
                    # Closed circle with coordinates sorted counter-clockwise
                    contour = np.array([ur, ul, ll, lr, ur])
                    polygon = shapely.geometry.Polygon(contour)
                    segmentations[obj.id] = {
                        'segmentation_layer_id': segmentation_layer.id,
                        'polygon': polygon
                    }

            with tm.utils.ExperimentConnection(self.experiment_id) as conn:
                logger.debug('delete existing mapobjects of type "%s"', name)
                tm.Mapobject.delete_cascade(conn, mapobject_type_id)
                logger.debug('add new mapobjects of type "%s"', name)
                for key, value in segmentations.iteritems():
                    mapobject_id = tm.Mapobject.add(
                        conn, mapobject_type_id, ref_id=key
                    )
                    logger.debug('add mapobject #%d', mapobject_id)
                    tm.MapobjectSegmentation.add(
                        conn, mapobject_id,
                        segmentation_layer_id=value['segmentation_layer_id'],
                        polygon=value['polygon']
                    )
