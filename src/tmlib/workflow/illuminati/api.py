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
from tmlib.image import IllumstatsImage
from tmlib.image import IllumstatsContainer
from tmlib.readers import DatasetReader
from tmlib.metadata import IllumstatsImageMetadata
from tmlib.workflow.api import ClusterRoutines
from tmlib.workflow.jobs import RunJob
from tmlib.workflow.jobs import RunJobCollection
from tmlib.workflow.jobs import MultiRunJobCollection
from tmlib.workflow.workflow import WorkflowStep

logger = logging.getLogger(__name__)


class PyramidBuilder(ClusterRoutines):

    def __init__(self, experiment_id, step_name, verbosity, **kwargs):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of the processed experiment
        step_name: str
            name of the corresponding step
        verbosity: int
            logging level
        **kwargs: dict
            ignored keyword arguments
        '''
        super(PyramidBuilder, self).__init__(
                experiment_id, step_name, verbosity)

    def list_input_files(self, job_descriptions):
        '''
        Provide a list of all input files that are required by the program.

        Parameters
        ----------
        job_descriptions: List[dict]
            job descriptions
        '''
        files = list()
        if job_descriptions['run']:
            run_files = utils.flatten([
                j['inputs'].values() for j in job_descriptions['run']
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
                                input_files.append(
                                    os.path.relpath(f.location, layer.location)
                                )
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
                                        os.path.join(tile_group, tile_file)
                                    )
                        else:
                            row_range = np.arange(layer.dimensions[level+1][0])
                            col_range = np.arange(layer.dimensions[level+1][1])
                            tile_coordinates = np.array(
                                list(itertools.product(row_range, col_range))
                            )[batch]
                            input_files = [
                                os.path.join(
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

    def create_jobs(self, job_descriptions,
                    duration=None, memory=None, cores=None):
        '''Create jobs that can be submitted for processing.

        Parameters
        ----------
        job_descriptions: Dict[List[dict]]
            description of inputs and outputs of individual computational jobs
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
        logger.info('create workflow step')

        logger.info('create jobs for "run" phase')
        multi_run_jobs = collections.defaultdict(list)
        for i, batch in enumerate(job_descriptions['run']):

            job = RunJob(
                    step_name=self.step_name,
                    arguments=self._build_run_command(batch),
                    output_dir=self.log_location,
                    job_id=batch['id'],
                    index=batch['index']
            )
            if duration:
                job.requested_walltime = Duration(duration)
            if memory:
                job.requested_memory = Memory(memory, Memory.GB)
            if cores:
                if not isinstance(cores, int):
                    raise TypeError(
                            'Argument "cores" must have type int.')
                if not cores > 0:
                    raise ValueError(
                            'The value of "cores" must be positive.')
                job.requested_cores = cores

            multi_run_jobs[batch['index']].append(job)

        run_jobs = MultiRunJobCollection(self.step_name)
        for index, jobs in multi_run_jobs.iteritems():
            run_jobs.add(
                RunJobCollection(self.step_name, jobs, index=index))

        return WorkflowStep(name=self.step_name, run_jobs=run_jobs)

    def _create_nonempty_base_level_tiles(self, batch):
        with tmlib.models.utils.Session() as session:
            layer = session.query(tmlib.models.ChannelLayer).\
                get(batch['layer_id'])

            logger.info(
                'create base level pyramid tiles for layer with '
                'time point %d, channel %s, z-plane %d',
                layer.tpoint, layer.channel.name, layer.zplane
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
                    logger.info('use default clip value: %d', clip_value)
                else:
                    clip_value = batch['clip_value']
                    logger.info('use provided clip value: %d', clip_value)
            else:
                clip_value = 2**16  # channel images are 16-bit

            if batch['illumcorr']:
                logger.info('correct images for illumination artifacts')
            if batch['align']:
                logger.info('align images between cycles')

        for fid in batch['image_file_ids']:
            with tmlib.models.utils.Session() as session:

                file = session.query(tmlib.models.ChannelImageFile).get(fid)
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
                    tile_file = session.get_or_create(
                        tmlib.models.PyramidTileFile,
                        name=name, group=group, row=t['row'],
                        column=t['column'], level=batch['level'],
                        channel_layer_id=file.channel_layer_id
                    )
                    tile = file.channel_layer.extract_tile_from_image(
                        image, t['y_offset'], t['x_offset']
                    )

                    # Tiles that overlap with other images.
                    if t['y_offset'] < 0 and t['x_offset'] >= 0:
                        logger.debug(
                            'tile "%s" overlaps 2 images vertically'
                            % tile_file.name
                        )
                        # above
                        extra_file = session.query(
                                tmlib.models.ChannelImageFile
                            ).\
                            join(tmlib.models.Site).\
                            filter(tmlib.models.ChannelImageFile.channel_layer_id == file.channel_layer_id).\
                            filter(tmlib.models.Site.y == file.site.y-1).\
                            filter(tmlib.models.Site.x == file.site.x).\
                            filter(tmlib.models.Site.well_id == file.site.well_id).\
                            one()
                        y = file.site.image_size[0] - abs(t['y_offset'])
                        x = t['x_offset']
                        height = abs(t['y_offset'])
                        width = tile.dimensions[1]
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
                        subtile = PyramidTile(
                            image.extract(y, x, height, width).pixels
                        )
                        tile = tile.insert(subtile, 0, 0)
                    elif t['y_offset'] >= 0 and t['x_offset'] < 0:
                        logger.debug(
                            'tile "%s" overlaps 2 images horizontally'
                            % tile_file.name
                        )
                        # to the left
                        extra_file = session.query(
                                tmlib.models.ChannelImageFile
                            ).\
                            join(tmlib.models.Site).\
                            filter(tmlib.models.ChannelImageFile.channel_layer_id == file.channel_layer_id).\
                            filter(tmlib.models.Site.y == file.site.y).\
                            filter(tmlib.models.Site.x == file.site.x-1).\
                            filter(tmlib.models.Site.well_id == file.site.well_id).\
                            one()
                        y = t['y_offset']
                        x = file.site.image_size[1] - abs(t['x_offset'])
                        height = tile.dimensions[0]
                        width = abs(t['x_offset'])
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
                            image = image_store[image.name]
                        subtile = PyramidTile(
                            image.extract(image, y, x, height, width).pixels
                        )
                        tile = tile.insert(subtile, 0, 0)
                    elif t['y_offset'] < 0 and t['x_offset'] < 0:
                        logger.debug(
                            'tile "%s" overlaps 4 images' % tile_file.name
                        )
                        # above
                        extra_file = session.query(
                                tmlib.models.ChannelImageFile
                            ).\
                            join(tmlib.models.Site).\
                            filter(tmlib.models.ChannelImageFile.channel_layer_id == file.channel_layer_id).\
                            filter(tmlib.models.Site.y == file.site.y-1).\
                            filter(tmlib.models.Site.x == file.site.x).\
                            filter(tmlib.models.Site.well_id == file.site.well_id).\
                            one()
                        y = file.site.image_size[0] - abs(t['y_offset'])
                        x = 0
                        height = abs(t['y_offset'])
                        width = tile.dimensions[1] - abs(t['x_offset'])
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
                        subtile = PyramidTile(
                            image.extract(image, y, x, height, width).pixels
                        )
                        tile = tile.insert(subtile, 0, abs(t['x_offset']))
                        # to the left
                        extra_file = session.query(
                                tmlib.models.ChannelImageFile
                            ).\
                            join(tmlib.models.Site).\
                            filter(tmlib.models.ChannelImageFile.channel_layer_id == file.channel_layer_id).\
                            filter(tmlib.models.Site.y == file.site.y).\
                            filter(tmlib.models.Site.x == file.site.x-1).\
                            filter(tmlib.models.Site.well_id == file.site.well_id).\
                            one()
                        y = 0
                        x = file.site.image_size[1] - abs(t['x_offset'])
                        height = tile.dimensions[0] - abs(t['y_offset'])
                        width = abs(t['x_offset'])
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
                        subtile = PyramidTile(
                            image.extract(image, y, x, height, width).pixels
                        )
                        tile = tile.insert(subtile, abs(t['x_offset']), 0)
                        # to the top left
                        extra_file = session.query(
                                tmlib.models.ChannelImageFile
                            ).\
                            join(tmlib.models.Site).\
                            filter(tmlib.models.ChannelImageFile.channel_layer_id == file.channel_layer_id).\
                            filter(tmlib.models.Site.y == file.site.y-1).\
                            filter(tmlib.models.Site.x == file.site.x-1).\
                            filter(tmlib.models.Site.well_id == file.site.well_id).\
                            one()
                        y = file.site.image_size[0] - abs(t['y_offset'])
                        x = file.site.image_size[1] - abs(t['x_offset'])
                        height = abs(t['y_offset'])
                        width = abs(t['x_offset'])
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
                        subtile = PyramidTile(
                            image.extract(image, y, x, height, width).pixels
                        )
                        tile = tile.insert(subtile, 0, 0)

                    # TODO: store ids of images that intersect with the tile
                    # as postgis polygons???

                    # Store tile file
                    tile_file.put(tile, session)

    def _create_empty_base_level_tiles(self, batch):
        pass

    def _create_higher_level_tiles(self, batch):
        pass

    def run_job(self, batch):
        '''Create 8-bit grayscale JPEG pyramid tiles.

        Parameters
        ----------
        batch: dict
            job_descriptions element
        '''
        if batch['index'] == 0:
            if batch['image_file_ids']:
                self._create_nonempty_base_level_tiles(batch)
            else:
                self._create_empty_base_level_tiles()
        
        else:
            # NOTE: Here we pass the "output" files to the function!
            self._create_higher_level_tiles(
                    batch['level'], filenames=batch['outputs']['image_files'])

    @utils.notimplemented
    def collect_job_output(self, batch):
        pass

    @utils.notimplemented
    def apply_statistics(self, output_dir, plates, wells, sites, channels,
                         tpoints, zplanes, **kwargs):
        pass
