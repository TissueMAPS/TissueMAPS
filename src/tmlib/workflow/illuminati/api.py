import os
import logging
import numpy as np
import collections
import itertools
import shapely.geometry
import sqlalchemy.orm
from sqlalchemy import func
from sqlalchemy.orm.exc import NoResultFound
from gc3libs.quantity import Duration
from gc3libs.quantity import Memory

import tmlib.models as tm
from tmlib import utils
from tmlib.image import PyramidTile
from tmlib.image import Image
from tmlib.errors import DataIntegrityError
from tmlib.errors import WorkflowError
from tmlib.workflow.api import ClusterRoutines
from tmlib.workflow.jobs import RunJob
from tmlib.workflow.jobs import SingleRunJobCollection
from tmlib.workflow.jobs import MultiRunJobCollection
from tmlib.workflow.jobs import CollectJob
from tmlib.workflow import register_api

logger = logging.getLogger(__name__)


@register_api('illuminati')
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
            run_files = utils.flatten([
                self._make_paths_absolute(j)['inputs'].values()
                for j in batches['run']
                if j['index'] == 0  # only base tile inputs
            ])
            if all([isinstance(f, list) for f in run_files]):
                run_files = utils.flatten(run_files)
                if all([isinstance(f, list) for f in run_files]):
                    run_files = utils.flatten(run_files)
                files.extend(run_files)
            elif any([isinstance(f, dict) for f in run_files]):
                files.extend(utils.flatten([
                    utils.flatten(f.values())
                    for f in run_files if isinstance(f, dict)
                ]))
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
        logger.info('perform data integrity tests')
        with tm.utils.Session() as session:
            n_images_per_site = session.query(func.count(tm.ChannelImageFile.id)).\
                join(tm.Channel).\
                filter(tm.Channel.experiment_id == self.experiment_id).\
                group_by(tm.ChannelImageFile.site_id).\
                all()
            if len(set(n_images_per_site)) > 1:
                raise DataIntegrityError(
                    'The number of channel image files must be the same for '
                    'each site!'
                )
            n_wells_per_plate = session.query(func.count(tm.Well.id)).\
                join(tm.Plate).\
                filter(tm.Plate.experiment_id == self.experiment_id).\
                group_by(tm.Plate.id).\
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
        with tm.utils.Session() as session:

            channel_ids = session.query(tm.Channel.id).\
                filter(tm.Channel.experiment_id == self.experiment_id).\
                distinct()

            for cid in channel_ids:

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

                    for index, level in enumerate(reversed(range(layer.n_levels))):
                        logger.debug('pyramid level %d', level)
                        # The layer "level" increases from top to bottom.
                        # We build the layer bottom-up, therefore, the "index"
                        # decreases from top to bottom.
                        if level == layer.maxzoom_level_index:
                            layer.create_tile_groups()
                            layer.create_image_properties_file()
                            # For the base level, batches are composed of
                            # image files, which will get chopped into tiles.
                            batches = self._create_batches(
                                np.arange(len(image_files)), args.batch_size
                            )
                        else:
                            # For the subsequent levels, batches are composed of
                            # tiles of the previous, next higher level.
                            # Therefore, the batch size needs to be adjusted.
                            batches = self._create_batches(
                                np.arange(np.prod(layer.dimensions[level])),
                                args.batch_size * 10 * level
                            )

                        for batch in batches:
                            job_count += 1
                            # For the highest resolution level, the inputs
                            # are channel image files. For all other levels,
                            # the inputs are the layer tiles of the next higher
                            # resolution level.
                            # For consistency, the paths to both types of image
                            # files are provided relative to the root layer
                            # directory.
                            if level == layer.maxzoom_level_index:
                                image_file_subset = np.array(image_files)[batch]
                                input_files = list()
                                output_files = list()
                                for f in image_file_subset:
                                    input_files.append(f.location)
                                    tiles = layer.map_image_to_base_tiles(f)
                                    for t in tiles:
                                        tile_file = layer.build_tile_file_name(
                                            level, t['row'], t['column']
                                        )
                                        tile_group = layer.build_tile_group_name(
                                            layer.tile_coordinate_group_map[
                                                level, t['row'], t['column']
                                            ]
                                        )
                                        output_files.append(
                                            os.path.join(
                                                layer.location,
                                                tile_group, tile_file
                                            )
                                        )
                            else:
                                row_range = np.arange(layer.dimensions[level+1][0])
                                col_range = np.arange(layer.dimensions[level+1][1])
                                tile_coordinates = np.array(
                                    list(itertools.product(row_range, col_range))
                                )[batch]
                                input_files = [
                                    os.path.join(
                                        layer.location,
                                        layer.build_tile_group_name(
                                            layer.tile_coordinate_group_map[
                                                level+1, c[0], c[1]
                                            ]
                                        ),
                                        layer.build_tile_file_name(
                                            level+1, c[0], c[1]
                                        )
                                    )
                                    for c in tile_coordinates
                                ]
                                row_range = np.arange(layer.dimensions[level][0])
                                col_range = np.arange(layer.dimensions[level][1])
                                tile_coordinates = np.array(
                                    list(itertools.product(row_range, col_range))
                                )[batch]
                                output_files = [
                                    os.path.join(
                                        layer.location,
                                        layer.build_tile_group_name(
                                            layer.tile_coordinate_group_map[
                                                level, c[0], c[1]
                                            ]
                                        ),
                                        layer.build_tile_file_name(
                                            level, c[0], c[1]
                                        )
                                    )
                                    for c in tile_coordinates
                                ]

                            description = {
                                'id': job_count,
                                'inputs': {
                                    'image_files': input_files
                                },
                                'outputs': {
                                    'image_files': output_files
                                },
                                'layer_id': layer.id,
                                'level': level,
                                'index': index
                            }
                            if level == layer.maxzoom_level_index:
                                # Only base tiles need to be corrected for
                                # illumination artifacts and aligned, this then
                                # automatically translates to the subsequent levels
                                description.update({
                                    'image_file_ids': [
                                        f.id for f in image_file_subset
                                    ],
                                    'align': args.align,
                                    'illumcorr': args.illumcorr,
                                    'clip': args.clip,
                                    'clip_value': args.clip_value,
                                    'clip_percent': args.clip_percent
                                })
                            job_descriptions['run'].append(description)

                        # if level == layer.maxzoom_level_index:
                        #     # Creation of empty base tiles, i.e. tiles that
                        #     # don't map to images
                        #     coordinates = layer.get_empty_base_tile_coordinates()
                        #     batches = self._create_batches(
                        #         list(coordinates), args.batch_size * 100
                        #     )
                        #     for batch in batches:
                        #         job_count += 1
                        #         job_descriptions['run'].append({
                        #             'id': job_count,
                        #             'inputs': {},
                        #             'outputs': {
                        #                 'image_files': [
                        #                     os.path.join(
                        #                         layer.location,
                        #                         layer.build_tile_group_name(
                        #                             layer.tile_coordinate_group_map[
                        #                                 level, y, x
                        #                             ]
                        #                         ),
                        #                         layer.build_tile_file_name(
                        #                             level, y, x
                        #                         )
                        #                     )
                        #                     for y, x in batch
                        #                 ]
                        #             },
                        #             'layer_id': layer.id,
                        #             'level': level,
                        #             'index': index,
                        #             'clip_value': None,
                        #             'clip_percent': None
                        #         })
        job_descriptions['collect'] = {'inputs': {}, 'outputs': {}}
        return job_descriptions

    def delete_previous_job_output(self):
        '''Deletes all instances of class
        :py:class:`tm.ChannelLayer` and
        :py:class:`tm.MapobjectType` as well as all children
        instances for the processed experiment.
        '''
        with tm.utils.Session() as session:

            channel_ids = session.query(tm.Channel.id).\
                filter_by(experiment_id=self.experiment_id).\
                all()
            channel_ids = [p[0] for p in channel_ids]

        if channel_ids:

            with tm.utils.Session() as session:

                logger.debug('delete existing channel layers')
                session.query(tm.ChannelLayer).\
                    filter(tm.ChannelLayer.channel_id.in_(channel_ids)).\
                    delete()

    def create_run_jobs(self, submission_id, user_name, batches,
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
        logger.info('create run jobs for submission %d', submission_id)
        logger.debug('allocated time for run jobs: %s', duration)
        logger.debug('allocated memory for run jobs: %d MB', memory)
        logger.debug('allocated cores for run jobs: %d', cores)

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

        run_jobs = MultiRunJobCollection(
            step_name=self.step_name,
            submission_id=submission_id
        )
        for index, jobs in multi_run_jobs.iteritems():
            run_jobs.add(
                SingleRunJobCollection(
                    step_name=self.step_name,
                    jobs=jobs,
                    index=index,
                    submission_id=submission_id
                )
            )

        return run_jobs

    def _create_maxzoom_level_tiles(self, batch):
        with tm.utils.Session() as session:
            layer = session.query(tm.ChannelLayer).get(batch['layer_id'])
            logger.info(
                'process layer: channel=%d, zplane=%d, tpoint=%d',
                layer.channel.index, layer.zplane, layer.tpoint
            )
            logger.info(
                'create non-empty tiles at maximum zoom level %d',
                batch['level']
            )

            if batch['clip'] or batch['illumcorr']:
                # Illumination statistics may not have been calculated
                # are are not required in case fixed clip value is provided.
                if batch['clip_value'] is None or batch['illumcorr']:
                    try:
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
            else:
                stats = None

            if batch['clip']:
                logger.info('clip intensity values')
                if batch['clip_value'] is None:
                    clip_above = stats.get_closest_percentile(
                        batch['clip_percent']
                    )
                    # If pixel values are too low for the channel,
                    # the channel is probably "empty"
                    # (for example because the staining didn't work).
                    # In this case we want to prevent that too extreme
                    # rescaling is applied, which would look shitty.
                    # The choice of the threshold level is totally arbitrary.
                    if clip_above < 200:
                        clip_above = 1000
                    logger.info('use default clip value: %d', clip_above)
                else:
                    clip_above = batch['clip_value']
                    logger.info('use provided clip value: %d', clip_above)
                if stats is not None:
                    clip_below = stats.get_closest_percentile(0.001)
                else:
                    clip_below = 0
            else:
                clip_above = 2**layer.channel.bit_depth - 1
                clip_below = 0

            layer.max_intensity = clip_above
            layer.min_intensity = clip_below

            if batch['illumcorr']:
                logger.info('correct images for illumination artifacts')
            if batch['align']:
                logger.info('align images between cycles')

        for fid in batch['image_file_ids']:
            with tm.utils.Session() as session:
                layer = session.query(tm.ChannelLayer).get(batch['layer_id'])

                file = session.query(tm.ChannelImageFile).get(fid)
                logger.info('process image "%s"', file.name)
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
                    image = image.clip(clip_below, clip_above)
                    image = image.scale(clip_below, clip_above)
                image_store[file.name] = image

                extra_file_map = layer.map_base_tile_to_images(file.site)
                for t in tiles:
                    name = layer.build_tile_file_name(
                        batch['level'], t['row'], t['column']
                    )
                    group = layer.tile_coordinate_group_map[
                        batch['level'], t['row'], t['column']
                    ]
                    tile_file = session.get_or_create(
                        tm.PyramidTileFile,
                        name=name, group=group,
                        row=t['row'], column=t['column'],
                        level=batch['level'],
                        channel_layer_id=layer.id
                    )
                    logger.debug('create tile: %s', tile_file.name)
                    tile = layer.extract_tile_from_image(
                        image_store[file.name], t['y_offset'], t['x_offset']
                    )

                    # Determine files that contain overlapping pixels,
                    # i.e. pixels falling into the currently processed tile
                    # that are not contained by the file.
                    file_coordinate = np.array((file.site.y, file.site.x))
                    extra_file_ids = extra_file_map[
                        tile_file.row, tile_file.column
                    ]
                    if len(extra_file_ids) > 0:
                        logger.debug('tile overlaps multiple images')
                    for efid in extra_file_ids:
                        extra_file = session.query(tm.ChannelImageFile).\
                            get(efid)
                        if extra_file.name not in image_store:
                            image = extra_file.get(z=layer.zplane)
                            if batch['illumcorr']:
                                logger.debug('correct image')
                                image = image.correct(stats)
                            if batch['align']:
                                logger.debug('align image')
                                image = image.align(crop=False)
                            if not image.is_uint8:
                                image = image.clip(clip_below, clip_above)
                                image = image.scale(clip_below, clip_above)
                            image_store[extra_file.name] = image

                        extra_file_coordinate = np.array((
                            extra_file.site.y, extra_file.site.x
                        ))

                        condition = file_coordinate > extra_file_coordinate
                        pixels = image_store[extra_file.name]
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
                                'Tile "%s" shouldn\'t be in this batch!'
                                % tile_file.name
                            )

                    tile_file.put(tile)

    # def _create_empty_maxzoom_level_tiles(self, batch):
    #     with tm.utils.Session() as session:

    #         layer = session.query(tm.ChannelLayer).get(batch['layer_id'])

    #         logger.info(
    #             'processing layer: channel=%d, zplane=%d, tpoint=%d',
    #             layer.channel.index, layer.zplane, layer.tpoint
    #         )
    #         logger.info(
    #             'creating empty tiles at maximum zoom level %d', batch['level']
    #         )

    #         for filename in batch['outputs']['image_files']:
    #             name = os.path.basename(filename)
    #             level, row, column = layer.get_coordinate_from_name(name)
    #             if level != batch['level']:
    #                 raise ValueError('Level doesn\'t match!')
    #             group = layer.tile_coordinate_group_map[level, row, column]
    #             tile_file = session.get_or_create(
    #                 tm.PyramidTileFile,
    #                 name=name, group=group, row=row,
    #                 column=column, level=batch['level'],
    #                 channel_layer_id=layer.id
    #             )
    #             logger.debug('creating tile: %s', tile_file.name)
    #             tile = PyramidTile.create_as_background()
    #             tile_file.put(tile)

    def _create_lower_zoom_level_tiles(self, batch):
        with tm.utils.Session() as session:
            layer = session.query(tm.ChannelLayer).get(batch['layer_id'])
            logger.info(
                'processing layer: channel %d', layer.channel.index
            )
            logger.info('creating tiles at zoom level %d', batch['level'])

        for f in batch['outputs']['image_files']:
            with tm.utils.Session() as session:
                layer = session.query(tm.ChannelLayer).\
                    get(batch['layer_id'])
                name = os.path.basename(f)
                level, row, column = layer.get_coordinate_from_name(name)
                if level != batch['level']:
                    raise ValueError('Level doesn\'t match!')
                coordinates = layer.calc_coordinates_of_next_higher_level(
                    level, row, column
                )
                group = layer.tile_coordinate_group_map[
                    level, row, column
                ]
                tile_file = session.get_or_create(
                    tm.PyramidTileFile,
                    name=name, group=group, row=row,
                    column=column, level=level,
                    channel_layer_id=layer.id
                )
                logger.debug('creating tile: %s', tile_file.name)
                rows = np.unique([c[0] for c in coordinates])
                cols = np.unique([c[1] for c in coordinates])
                # Build the mosaic by loading required higher level tiles
                # (created in a previous run) and stitching them together
                for i, r in enumerate(rows):
                    for j, c in enumerate(cols):
                        try:
                            pre_tile_file = session.query(tm.PyramidTileFile).\
                                filter_by(
                                    row=r, column=c, level=batch['level']+1,
                                    channel_layer_id=layer.id
                                ).\
                                one()
                            pre_tile = pre_tile_file.get()
                        except sqlalchemy.orm.exc.NoResultFound:
                            # Tiles at maxzoom level might not exist in case
                            # they are empty. They must exist at the lower
                            # levels however.
                            if batch['index'] > 1:
                                raise ValueError(
                                    'Tile "%s" was not created.'
                                    % layer.build_tile_file_name(
                                        batch['level']+1, r, c
                                    )
                                )
                            logger.warning(
                                'tile "%s" was not created - might be empty',
                                layer.build_tile_file_name(
                                    batch['level']+1, r, c
                                )
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
                tile = PyramidTile(mosaic_img.shrink(layer.zoom_factor).array)
                tile_file.put(tile)

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
        '''Creates default instances of :py:class:`tm.MapobjectType`
        for :py:class:`tm.Site`, :py:class:`tm.Well`,
        and :py:class:`tm.Plate` and creates for each instance an
        instance of :py:class:`tm.Mapobject` and the corresponding
        :py:class:`tm.MapobjectSegmentation`.

        batch: dict
            job description
        '''
        with tm.utils.Session() as session:

            mapobject_types = session.query(tm.MapobjectType).\
                filter_by(experiment_id=self.experiment_id, is_static=True).\
                all()
            for m in mapobject_types:
                logger.debug('delete map object type: %r', m)
                session.delete(m)

        with tm.utils.Session() as session:

            layer = session.query(tm.ChannelLayer).\
                join(tm.Channel).\
                filter(tm.Channel.experiment_id == self.experiment_id).\
                first()

            mapobjects = {
                'Plate':
                    session.query(tm.Plate).
                    filter(tm.Plate.experiment_id == self.experiment_id),
                'Wells':
                    session.query(tm.Well).
                    join(tm.Plate).
                    filter(tm.Plate.experiment_id == self.experiment_id),
                'Sites':
                    session.query(tm.Site).
                    join(tm.Well).
                    join(tm.Plate).
                    filter(tm.Plate.experiment_id == self.experiment_id)
            }

            for name, query in mapobjects.iteritems():

                logger.info('create mapobject type "%s"', name)
                mapobject_type = session.get_or_create(
                    tm.MapobjectType,
                    name=name, experiment_id=self.experiment_id, is_static=True
                )
                session.add(mapobject_type)
                session.flush()

                logger.info('create mapobjects of type "%s"', name)
                mapobject_outlines = list()
                for obj in query:

                    mapobject = tm.Mapobject(mapobject_type_id=mapobject_type.id)
                    session.add(mapobject)
                    session.flush()
                    # First element: x axis
                    # Second element: inverted y axis
                    ul = (obj.offset[1], -1 * obj.offset[0])
                    ll = (ul[0] + obj.image_size[1], ul[1])
                    ur = (ul[0], ul[1] - obj.image_size[0])
                    lr = (ll[0], ul[1] - obj.image_size[0])
                    # Closed circle with coordinates sorted counter-clockwise
                    contour = np.array([ur, ul, ll, lr, ur])
                    polygon = shapely.geometry.Polygon(contour)
                    mapobject_outlines.append(
                        tm.MapobjectSegmentation(
                            mapobject_id=mapobject.id,
                            geom_poly=polygon.wkt,
                            geom_centroid=polygon.centroid.wkt
                        )
                    )
                session.add_all(mapobject_outlines)
                session.flush()

                min_zoom, max_zoom = mapobject_type.calculate_min_max_poly_zoom(
                    layer.maxzoom_level_index,
                    segmentation_ids=[o.id for o in mapobject_outlines]
                )
                mapobject_type.min_poly_zoom = min_zoom
                mapobject_type.max_poly_zoom = max_zoom

