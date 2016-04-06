import os
import logging
import numpy as np
import collections
import itertools
import sqlalchemy.orm
from gc3libs.quantity import Duration
from gc3libs.quantity import Memory

import tmlib.models as tm
from tmlib import utils
from tmlib.image import PyramidTile
from tmlib.image import ChannelImage
from tmlib.workflow.api import ClusterRoutines
from tmlib.workflow.jobs import RunJob
from tmlib.workflow.jobs import SingleRunJobCollection
from tmlib.workflow.jobs import MultiRunJobCollection
from tmlib.workflow.jobs import CollectJob

logger = logging.getLogger(__name__)


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
        logger.debug('create descriptions for "run" jobs')
        job_descriptions = dict()
        job_descriptions['run'] = list()
        job_count = 0
        with tm.utils.Session() as session:

            metadata = session.query(
                    tm.ChannelImageFile.tpoint,
                    tm.ChannelImageFile.zplane,
                    tm.ChannelImageFile.channel_id,
                ).\
                join(tm.Channel).\
                filter(tm.Channel.experiment_id == self.experiment_id).\
                distinct()

            for attributes in metadata:

                layer = session.get_or_create(
                    tm.ChannelLayer,
                    tpoint=attributes.tpoint, zplane=attributes.zplane,
                    channel_id=attributes.channel_id
                )

                image_files = session.query(tm.ChannelImageFile).\
                    filter_by(
                        tpoint=layer.tpoint, zplane=layer.zplane,
                        channel_id=layer.channel_id
                    ).\
                    all()

                for index, level in enumerate(reversed(range(layer.n_levels))):
                    # NOTE: The pyramid "level" increases from top to bottom.
                    # We build the pyramid bottom-up, therefore, the "index"
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
                        # NOTE: For the highest resolution level, the inputs
                        # are channel image files. For all other levels,
                        # the inputs are the pyramid tiles of the next higher
                        # resolution level (the ones created in the prior run).
                        # For consistency, the paths to both types of image
                        # files are provided relative to the root pyramid
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

                        # NOTE: Keeping track of inputs/outputs for each job
                        # is problematic because the number of tiles increases
                        # exponentially with the number of image files.

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
                                'image_file_ids': [f.id for f in image_files],
                                'align': args.align,
                                'illumcorr': args.illumcorr,
                                'clip': args.clip,
                                'clip_value': args.clip_value,
                            })
                        job_descriptions['run'].append(description)

                    if level == layer.maxzoom_level_index:
                        coordinates = layer.get_empty_base_tile_coordinates()
                        # Creation of empty base tiles that don't map to images
                        job_count += 1
                        job_descriptions['run'].append({
                            'id': job_count,
                            'inputs': {},
                            'outputs': {
                                'image_files': [
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
                                    for c in coordinates
                                ]
                            },
                            'layer_id': layer.id,
                            'level': level,
                            'index': index,
                            'clip_value': None
                        })
        job_descriptions['collect'] = {'inputs': dict(), 'outputs': dict()}
        return job_descriptions

    def delete_previous_job_output(self):
        '''Deletes all instances of class
        :py:class:`tm.ChannelLayer` and
        :py:class:`tm.MapobjectType` as well as all children
        instances for the processed experiment.
        '''
        with tm.utils.Session() as session:

            layer = session.query(tm.ChannelLayer).\
                join(tm.Channel).\
                filter(tm.Channel.experiment_id == self.experiment_id).\
                all()
            for l in layer:
                logger.debug('delete channel layer: %r', l)
                session.delete(l)

            mapobject_types = session.query(tm.MapobjectType).\
                filter_by(experiment_id=self.experiment_id).\
                all()
            for m in mapobject_types:
                logger.debug('delete map object type: %r', m)
                session.delete(m)

    def create_jobs(self, step, batches,
                    duration=None, memory=None, cores=None):
        '''Creates jobs that can be submitted for processing.

        Parameters
        ----------
        step: tmlib.workflow.WorkflowStep
            the step to which jobs should be added
        batches: Dict[List[dict]]
            job descriptions
        duration: str, optional
            computational time that should be allocated for a single job;
            in HH:MM:SS format (default: ``None``)
        memory: int, optional
            amount of memory in Megabyte that should be allocated for a single
            job (default: ``None``)
        cores: int, optional
            number of CPU cores that should be allocated for a single job
            (default: ``None``)

        Returns
        -------
        tmlib.tmaps.workflow.WorkflowStep
            collection of jobs
        '''
        logger.info('create jobs for "run" phase')
        multi_run_jobs = collections.defaultdict(list)
        for i, batch in enumerate(batches['run']):

            job = RunJob(
                step_name=self.step_name,
                arguments=self._build_run_command(batch),
                output_dir=self.log_location,
                job_id=batch['id'],
                index=batch['index'],
                submission_id=step.submission_id
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

            multi_run_jobs[batch['index']].append(job)

        step.run_jobs = MultiRunJobCollection(
            step_name=self.step_name,
            submission_id=step.submission_id
        )
        for index, jobs in multi_run_jobs.iteritems():
            step.run_jobs.add(
                SingleRunJobCollection(
                    step_name=self.step_name,
                    jobs=jobs,
                    index=index,
                    submission_id=step.submission_id
                )
            )

        logger.info('create job for "collect" phase')
        batch = batches['collect']

        step.collect_job = CollectJob(
            step_name=self.step_name,
            arguments=self._build_collect_command(),
            output_dir=self.log_location,
            submission_id=step.submission_id
        )
        step.collect_job.requested_walltime = Duration('02:00:00')
        step.collect_job.requested_memory = Memory(3800, Memory.MB)

        return step

    def _create_nonempty_maxzoom_level_tiles(self, batch):
        with tm.utils.Session() as session:
            layer = session.query(tm.ChannelLayer).\
                get(batch['layer_id'])
            logger.info(
                'processing layer: channel %d, time point %d, z-plane %d',
                layer.channel.index, layer.tpoint, layer.zplane
            )
            logger.info(
                'creating non-empty tiles at maximum zoom level %d',
                batch['level']
            )

            if batch['illumcorr'] or (batch['clip'] and not batch['clip_value']):
                illumstats_file = session.query(tm.IllumstatsFile).\
                    filter_by(
                        channel_id=layer.channel_id,
                        cycle_id=layer.channel.image_files[0].cycle_id
                    ).\
                    one()
                stats = illumstats_file.get()

            if batch['clip']:
                logger.info('clip intensity values')
                if batch['clip_value'] is None:
                    clip_value = stats.percentiles[99.999]
                    logger.info('using default clip value: %d', clip_value)
                else:
                    clip_value = batch['clip_value']
                    logger.info('using provided clip value: %d', clip_value)
            else:
                clip_value = 2**16  # channel images are 16-bit

            if batch['illumcorr']:
                logger.info('correcting images for illumination artifacts')
            if batch['align']:
                logger.info('aligning images between cycles')

        for fid in batch['image_file_ids']:
            with tm.utils.Session() as session:

                layer = session.query(tm.ChannelLayer).\
                    get(batch['layer_id'])

                file = session.query(tm.ChannelImageFile).get(fid)
                logger.info('process image "%s"', file.name)
                mapped_tiles = layer.map_image_to_base_tiles(file)
                image_store = dict()
                image = file.get()
                if batch['illumcorr']:
                    image = image.correct(stats)
                if batch['align']:
                    image = image.align(crop=False)
                image = image.clip(clip_value)
                image = image.scale(clip_value)
                image_store[file.name] = image
                for t in mapped_tiles:
                    name = layer.build_tile_file_name(
                        batch['level'], t['row'], t['column']
                    )
                    group = layer.tile_coordinate_group_map[
                        batch['level'], t['row'], t['column']
                    ]
                    tile_file = session.get_or_create(
                        tm.PyramidTileFile,
                        name=name, group=group, row=t['row'],
                        column=t['column'], level=batch['level'],
                        channel_layer_id=layer.id
                    )
                    logger.info('creating tile: %s', tile_file.name)
                    tile = layer.extract_tile_from_image(
                        image_store[file.name], t['y_offset'], t['x_offset']
                    )

                    file_coordinate = np.array((file.site.y, file.site.x))
                    # TODO: calculate this only for the local neighborhood
                    # of the file rather than for all files!
                    extra_files = layer.base_tile_coordinate_to_image_file_map[
                        (tile_file.row, tile_file.column)
                    ]
                    extra_files.remove(file)  # remove the current file
                    if len(extra_files) > 0:
                        logger.info('tile overlaps multiple images')
                    for extra_file in extra_files:
                        if extra_file.name not in image_store:
                            image = extra_file.get()
                            if batch['illumcorr']:
                                image = image.correct(stats)
                            if batch['align']:
                                image = image.align(crop=False)
                            image = image.clip(clip_value)
                            image = image.scale(clip_value)
                            image_store[extra_file.name] = image

                        extra_file_coordinate = np.array((
                            extra_file.site.y, extra_file.site.x
                        ))
                        condition = file_coordinate > extra_file_coordinate
                        # Each batch only processes the overlapping tiles
                        # at the upper and/or left border of images.
                        if all(condition):
                            logger.debug('insert pixels from top left image')
                            y = file.site.image_size[0] - abs(t['y_offset'])
                            x = file.site.image_size[1] - abs(t['x_offset'])
                            height = abs(t['y_offset'])
                            width = abs(t['x_offset'])
                            subtile = PyramidTile(
                                image_store[extra_file.name].extract(
                                    y, x, height, width
                                ).pixels
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
                                image_store[extra_file.name].extract(
                                    y, x, height, width
                                ).pixels
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
                                image_store[extra_file.name].extract(
                                    y, x, height, width
                                ).pixels
                            )
                            tile.insert(subtile, y_offset, 0)
                        else:
                            raise IndexError(
                                'Tile "%s" shouldn\'t be in this batch!'
                                % tile_file.name
                            )

                    tile_file.put(tile)

    def _create_empty_maxzoom_level_tiles(self, batch):
        with tm.utils.Session() as session:

            layer = session.query(tm.ChannelLayer).\
                get(batch['layer_id'])

            logger.info(
                'processing layer: channel %d, time point %d, z-plane %d',
                layer.channel.index, layer.tpoint, layer.zplane
            )
            logger.info(
                'creating empty tiles at maximum zoom level %d', batch['level']
            )

            missing_tile_coords = layer.get_empty_base_tile_coordinates()
            # TODO: add to batches!!!
            for t in missing_tile_coords:
                name = layer.build_tile_file_name(
                    batch['level'], t[0], t[1]
                )
                group = layer.tile_coordinate_group_map[
                    batch['level'], t[0], t[1]
                ]
                tile_file = session.get_or_create(
                    tm.PyramidTileFile,
                    name=name, group=group, row=t[0],
                    column=t[1], level=batch['level'],
                    channel_layer_id=layer.id
                )
                logger.info('create tile: %s', tile_file.name)
                tile = PyramidTile.create_as_background()
                tile_file.put(tile)

    def _create_lower_zoom_level_tiles(self, batch):
        with tm.utils.Session() as session:
            layer = session.query(tm.ChannelLayer).\
                get(batch['layer_id'])
            logger.info(
                'processing layer: channel %d, time point %d, z-plane %d',
                layer.channel.index, layer.tpoint, layer.zplane
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
                logger.info('creating tile: %s', tile_file.name)
                rows = np.unique([c[0] for c in coordinates])
                cols = np.unique([c[1] for c in coordinates])
                # Build the mosaic by loading required higher level tiles
                # (created in a previous run) and stitching them together
                for i, r in enumerate(rows):
                    for j, c in enumerate(cols):
                        try:
                            pre_tile_file = session.query(
                                    tm.PyramidTileFile
                                ).\
                                filter_by(
                                    row=r, column=c, level=batch['level']+1,
                                    channel_layer_id=layer.id
                                ).\
                                one()
                        except sqlalchemy.orm.exc.NoResultFound:
                            raise ValueError(
                                'Tile "%s" was not created!'
                                % layer.build_tile_file_name(
                                    batch['level']+1, r, c
                                )
                            )
                        # We have to temporally treat it as an "image",
                        # since a tile can per definition not be larger
                        # than 256x256 pixels.
                        img = ChannelImage(pre_tile_file.get().pixels)
                        if j == 0:
                            row_img = img
                        else:
                            row_img = row_img.join(img, 'horizontal')
                    if i == 0:
                        mosaic_img = row_img
                    else:
                        mosaic_img = mosaic_img.join(row_img, 'vertical')
                # Create the tile at the current level by downsampling the
                # mosaic image, which is composed of the 4 tiles of the next
                # higher zoom level
                tile = PyramidTile(mosaic_img.shrink(layer.zoom_factor).pixels)
                tile_file.put(tile)

    def run_job(self, batch):
        '''Create 8-bit grayscale JPEG pyramid tiles.

        Parameters
        ----------
        batch: dict
            batches element
        '''
        if batch['index'] == 0:
            if batch.get('image_file_ids', None):
                self._create_nonempty_maxzoom_level_tiles(batch)
            else:
                self._create_empty_maxzoom_level_tiles(batch)
        else:
            self._create_lower_zoom_level_tiles(batch)

    def collect_job_output(self, batch):
        '''Creates default instances of :py:class:`tm.MapobjectType`
        for :py:class:`tm.Site`, :py:class:`tm.Well`,
        and :py:class:`tm.Plate` and creates for each instance an
        instance of :py:class:`tm.Mapobject` and the corresponding
        :py:class:`tm.MapobjectOutline`.

        batch: dict
            job description
        '''
        with tm.utils.Session() as session:

            mapobject_types = session.query(tm.MapobjectType).\
                filter_by(experiment_id=self.experiment_id, static=True).\
                all()
            for m in mapobject_types:
                logger.debug('delete map object type: %r', m)
                session.delete(m)

        with tm.utils.Session() as session:

            logger.info('create mapobject type "Plates"')
            plates_mapobject_type = session.get_or_create(
                tm.MapobjectType,
                name='Plates', experiment_id=self.experiment_id,
                static=True
            )
            session.add(plates_mapobject_type)
            session.flush()

            plates = session.query(tm.Plate).\
                filter(tm.Plate.experiment_id == self.experiment_id)
            logger.info('create mapobjects of type "Plates"')
            for plate in plates:

                plate_mapobject = tm.Mapobject(
                    mapobject_type_id=plates_mapobject_type.id
                )
                session.add(plate_mapobject)
                session.flush()
                # NOTE: first element: x axis; second element: inverted y axis
                ul = (plate.offset[1], -1 * plate.offset[0])
                ll = (ul[0] + plate.image_size[1], ul[1])
                ur = (ul[0], ul[1] - plate.image_size[0])
                lr = (ll[0], ul[1] - plate.image_size[0])
                plate_poly = 'POLYGON((%s))' % ','.join([
                    '%d %d' % ur, '%d %d' % ul, '%d %d' % ll, '%d %d' % lr,
                    '%d %d' % ur
                ])
                plate_centroid = 'POINT(%.2f %.2f)' % (
                    np.mean([ul[1], ll[1]]), np.mean([ul[0], ur[0]])
                )
                plates_mapobject_outline = tm.MapobjectOutline(
                    mapobject_id=plate_mapobject.id,
                    geom_poly=plate_poly, geom_centroid=plate_centroid
                )
                session.add(plates_mapobject_outline)

        with tm.utils.Session() as session:

            logger.info('create mapobject type "Wells"')
            wells_mapobject_type = session.get_or_create(
                tm.MapobjectType,
                name='Wells', experiment_id=self.experiment_id, static=True
            )
            session.add(wells_mapobject_type)
            session.flush()

            wells = session.query(tm.Well).\
                join(tm.Plate).\
                filter(tm.Plate.experiment_id == self.experiment_id)
            logger.info('create mapobjects of type "Wells"')
            for well in wells:

                well_mapobject = tm.Mapobject(
                    mapobject_type_id=wells_mapobject_type.id
                )
                session.add(well_mapobject)
                session.flush()
                ul = (well.offset[1], -1 * well.offset[0])
                ll = (ul[0] + well.image_size[1], ul[1])
                ur = (ul[0], ul[1] - well.image_size[0])
                lr = (ll[0], ul[1] - well.image_size[0])
                well_poly = 'POLYGON((%s))' % ','.join([
                    '%d %d' % ur, '%d %d' % ul, '%d %d' % ll, '%d %d' % lr,
                    '%d %d' % ur
                ])
                well_centroid = 'POINT(%.2f %.2f)' % (
                    np.mean([ul[1], ll[1]]), np.mean([ul[0], ur[0]])
                )
                well_mapobject_outline = tm.MapobjectOutline(
                    mapobject_id=well_mapobject.id,
                    geom_poly=well_poly, geom_centroid=well_centroid
                )
                session.add(well_mapobject_outline)

        with tm.utils.Session() as session:

            logger.info('create mapobject type "Sites"')
            sites_mapobject_type = session.get_or_create(
                tm.MapobjectType,
                name='Sites', experiment_id=self.experiment_id, static=True
            )
            session.add(sites_mapobject_type)
            session.flush()

            sites = session.query(tm.Site).\
                join(tm.Well).\
                join(tm.Plate).\
                filter(tm.Plate.experiment_id == self.experiment_id)
            logger.info('create mapobjects of type "Sites"')
            for site in sites:

                site_mapobject = tm.Mapobject(
                    mapobject_type_id=sites_mapobject_type.id
                )
                session.add(site_mapobject)
                session.flush()
                ul = (site.offset[1], -1 * site.offset[0])
                ll = (ul[0] + site.image_size[1], ul[1])
                ur = (ul[0], ul[1] - site.image_size[0])
                lr = (ll[0], ul[1] - site.image_size[0])
                site_poly = 'POLYGON((%s))' % ','.join([
                    '%d %d' % ur, '%d %d' % ul, '%d %d' % ll,
                    '%d %d' % lr, '%d %d' % ur
                ])
                site_centroid = 'POINT(%.2f %.2f)' % (
                    np.mean([ul[1], ll[1]]), np.mean([ul[0], ur[0]])
                )
                site_mapobject_outline = tm.MapobjectOutline(
                    mapobject_id=site_mapobject.id,
                    geom_poly=site_poly, geom_centroid=site_centroid
                )
                session.add(site_mapobject_outline)


def factory(experiment_id, verbosity, **kwargs):
    '''Factory function for the instantiation of a `illuminati`-specific
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
    tmlib.workflow.metaextract.api.PyramidBuilder
        API instance
    '''
    return PyramidBuilder(experiment_id, verbosity)
