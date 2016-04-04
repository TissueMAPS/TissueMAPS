import os
import logging
import numpy as np
import collections
import itertools
from gc3libs.quantity import Duration
from gc3libs.quantity import Memory

import tmlib.models
from tmlib import utils
from tmlib.image import PyramidTile
from tmlib.image import ChannelImage
from tmlib.workflow.api import ClusterRoutines
from tmlib.workflow.jobs import RunJob
from tmlib.workflow.jobs import RunJobCollection
from tmlib.workflow.jobs import SingleRunJobCollection
from tmlib.workflow.jobs import MultiRunJobCollection
from tmlib.workflow.workflow import WorkflowStep

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
        '''
        Provide a list of all input files that are required by the program.

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
        '''
        Create job descriptions for parallel computing.

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
        with tmlib.models.utils.Session() as session:

            for layer in session.query(tmlib.models.ChannelLayer).\
                    join(tmlib.models.Channel).\
                    join(tmlib.models.Experiment).\
                    filter(tmlib.models.Experiment.id == self.experiment_id):

                for index, level in enumerate(reversed(range(layer.n_levels))):
                    # NOTE: The pyramid "level" increases from top to bottom.
                    # We build the pyramid bottom-up, therefore, the "index"
                    # decreases from top to bottom.
                    if level == layer.base_level_index:
                        layer.create_tile_groups()
                        layer.create_image_properties_file()
                        # For the base level, batches are composed of
                        # image files, which will get chopped into tiles.
                        batches = self._create_batches(
                            np.arange(len(layer.image_files)),
                            args.batch_size
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
                        if level == layer.base_level_index:
                            image_files = np.array(layer.image_files)[batch]
                            input_files = list()
                            output_files = list()
                            for f in image_files:
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
                        if level == layer.base_level_index:
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

                    if level == layer.base_level_index:
                        # Creation of empty base tiles that don't map to images
                        job_count += 1
                        job_descriptions['run'].append({
                            'id': job_count,
                            'inputs': {},
                            'outputs': {},
                            'layer_id': layer.id,
                            'level': level,
                            'index': index,
                            'clip_value': None
                        })
        return job_descriptions

    def create_jobs(self, step, batches,
                    duration=None, memory=None, cores=None):
        '''Create jobs that can be submitted for processing.

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

        return step

    def _create_nonempty_maxzoom_level_tiles(self, batch):
        with tmlib.models.utils.Session() as session:
            layer = session.query(tmlib.models.ChannelLayer).\
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
                illumstats_file = session.query(tmlib.models.IllumstatsFile).\
                    filter_by(
                        channel_id=layer.channel_id,
                        cycle_id=layer.image_files[0].cycle_id
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
            with tmlib.models.utils.Session() as session:

                file = session.query(tmlib.models.ChannelImageFile).get(fid)
                logger.info('process image "%s"', file.name)
                mapped_tiles = file.channel_layer.map_image_to_base_tiles(file)
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
                    name = file.channel_layer.build_tile_file_name(
                        batch['level'], t['row'], t['column']
                    )
                    group = file.channel_layer.tile_coordinate_group_map[
                        batch['level'], t['row'], t['column']
                    ]
                    # TODO: only create if not at the lower and/or right border
                    tile_file = session.get_or_create(
                        tmlib.models.PyramidTileFile,
                        name=name, group=group, row=t['row'],
                        column=t['column'], level=batch['level'],
                        channel_layer_id=file.channel_layer_id
                    )
                    logger.info('creating tile: %s', tile_file.name)
                    tile = file.channel_layer.extract_tile_from_image(
                        image, t['y_offset'], t['x_offset']
                    )

                    file_coordinate = np.array((file.site.y, file.site.x))
                    # TODO: calculate this only for the local neighborhood
                    # of the file rather than for all files!
                    extra_files = file.channel_layer.\
                        maxzoom_tile_coordinate_to_image_file_map[
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
                        else:
                            image = image_store[extra_file.name]

                        extra_file_coordinate = np.array((
                            extra_file.site.y, extra_file.site.x
                        ))
                        condition = file_coordinate > extra_file_coordinate
                        if all(condition):
                            logger.debug('insert pixels from top left image')
                            y = file.site.image_size[0] - abs(t['y_offset'])
                            x = file.site.image_size[1] - abs(t['x_offset'])
                            height = abs(t['y_offset'])
                            width = abs(t['x_offset'])
                            subtile = PyramidTile(
                                image.extract(y, x, height, width).pixels
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
                                image.extract(y, x, height, width).pixels
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
                                image.extract(y, x, height, width).pixels
                            )
                            tile.insert(subtile, y_offset, 0)
                        else:
                            # Each job processes only the overlapping tiles
                            # at the upper and/or left border of the image.
                            # This prevents that tiles are created twice, which
                            # may cause problems with file locking and so on.
                            # The database entry was already created here, but
                            # we just leave it for the other job that will
                            # eventually (hopefully) process the tile.
                            continue

                    tile_file.put(tile)

    def _create_empty_maxzoom_level_tiles(self, batch):
        with tmlib.models.utils.Session() as session:

            layer = session.query(tmlib.models.ChannelLayer).\
                get(batch['layer_id'])

            logger.info(
                'processing layer: channel %d, time point %d, z-plane %d',
                layer.channel.index, layer.tpoint, layer.zplane
            )
            logger.info(
                'creating empty tiles at maximum zoom level %d', batch['level']
            )

            tile_coords = layer.maxzoom_tile_coordinate_to_image_file_map.keys()
            rows = range(layer.dimensions[-1][0])
            cols = range(layer.dimensions[-1][1])
            all_tile_coords = list(itertools.product(rows, cols))
            missing_tile_coords = set(all_tile_coords) - set(tile_coords)
            for t in missing_tile_coords:
                name = layer.build_tile_file_name(
                    batch['level'], t[0], t[1]
                )
                group = layer.tile_coordinate_group_map[
                    batch['level'], t[0], t[1]
                ]
                tile_file = session.get_or_create(
                    tmlib.models.PyramidTileFile,
                    name=name, group=group, row=t[0],
                    column=t[1], level=batch['level'],
                    channel_layer_id=layer.id
                )
                logger.info('create tile: %s', tile_file.name)
                tile = PyramidTile.create_as_background()
                tile_file.put(tile)

    def _create_lower_zoom_level_tiles(self, batch):
        with tmlib.models.utils.Session() as session:
            layer = session.query(tmlib.models.ChannelLayer).\
                get(batch['layer_id'])
            logger.info(
                'processing layer: channel %d, time point %d, z-plane %d',
                layer.channel.index, layer.tpoint, layer.zplane
            )
            logger.info('creating tiles at zoom level %d', batch['level'])

        for f in batch['outputs']['image_files']:
            with tmlib.models.utils.Session() as session:
                layer = session.query(tmlib.models.ChannelLayer).\
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
                    tmlib.models.PyramidTileFile,
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
                        pre_tile_file = session.query(
                                tmlib.models.PyramidTileFile
                            ).\
                            filter_by(
                                row=r, column=c, level=batch['level']+1,
                                channel_layer_id=layer.id
                            ).\
                            one()
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

    @utils.notimplemented
    def collect_job_output(self, batch):
        pass


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
