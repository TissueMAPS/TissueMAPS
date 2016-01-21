import os
import logging
import numpy as np
from cached_property import cached_property
from ..layer import ChannelLayer
from ..readers import DatasetReader
from ..api import ClusterRoutines

logger = logging.getLogger(__name__)


class PyramidBuilder(ClusterRoutines):

    def __init__(self, experiment, prog_name, verbosity, level=None):
        '''
        Initialize an instance of class PyramidBuilder.

        Parameters
        ----------
        experiment: tmlib.experiment.Experiment
            configured experiment object
        prog_name: str
            name of the corresponding program (command line interface)
        verbosity: int
            logging level
        level: int
            zero-based pyramid level index, where 0 represents the top pyramid
            level, i.e. the most zoomed out level with the lowest resolution
        '''
        super(PyramidBuilder, self).__init__(
                experiment, prog_name, verbosity)
        self.experiment = experiment
        self.prog_name = prog_name
        self.verbosity = verbosity
        self.level = level

    @cached_property
    def project_dir(self):
        '''
        Returns
        -------
        str
            directory where *.job* files and log output will be stored
        '''
        project_dir = os.path.join(self.experiment.dir,
                                         'tmaps', self.prog_name,
                                         'level_%d' % self.level)
        if not os.path.exists(project_dir):
            logger.debug('create project directory: %s' % project_dir)
            os.makedirs(project_dir)
        return project_dir

    def create_job_descriptions(self, args):
        '''
        Create job descriptions for parallel computing.

        Parameters
        ----------
        args: tmlib.illuminati.args.IlluminatiInitArgs
            program-specific arguments

        Returns
        -------
        Dict[str, List[dict] or dict]
            job descriptions
        '''
        logger.debug('create descriptions for "run" jobs')
        job_descriptions = dict()
        job_descriptions['run'] = list()
        job_count = 0
        for identifier in self.experiment.layer_names.keys():
            layer = ChannelLayer(
                            self.experiment,
                            tpoint_ix=identifier[0],
                            channel_ix=identifier[1],
                            zplane_ix=identifier[2]
            )
            if self.level == layer.base_level_index:
                layer.create_tile_groups()
                layer.create_image_properties_file()
                batches = self._create_batches(
                                range(len(layer.metadata.filenames)),
                                args.batch_size)
            else:
                level_batch_size = args.batch_size * 10 * self.level
                batches = self._create_batches(
                                range(len(layer.tile_files[self.level])),
                                level_batch_size)

            for batch in batches:
                job_count += 1
                # NOTE: For the highest resolution level, the input files are
                # the original microscope images. For all other levels,
                # the input files are the tiles of the next higher resolution
                # level (the ones created in the prior run).
                # For consistency, the paths to both types of image files
                # are provided relative to the root pyramid directory.
                if self.level == layer.base_level_index:
                    filenames = layer.metadata.filenames
                    filenames = list(np.array(filenames)[batch])
                    input_files = [
                        os.path.relpath(f, layer.dir)
                        for f in filenames
                    ]
                    # tile_mapping = layer.base_tile_mappings['image_to_tiles']
                    # output_files = [
                    #     layer.tile_files[self.level][c]
                    #     for f in input_files
                    #     for c in tile_mapping[os.path.basename(f)]
                    # ]
                else:
                    input_files = []
                # else:
                #     output_files = layer.tile_files[self.level].values()
                #     output_files = list(np.array(output_files)[batch])
                #     input_files = [
                #         layer.tile_files[self.level + 1][c]
                #         for f in output_files
                #         for c in layer.get_tiles_of_next_higher_level(f)
                #     ]

                # NOTE: keeping track of input/output files for each job
                # becomes problematic because the number of tiles increases
                # exponentially with the number of image files.
 
                description = {
                    'id': job_count,
                    'inputs': {
                        'image_files': [
                            os.path.join(layer.dir, f) for f in input_files
                        ]
                    },
                    # 'outputs': {
                    #     'image_files': [
                    #         os.path.join(layer.dir, f) for f in output_files
                    #     ]
                    # },
                    'outputs': {},
                    'cycle': layer.tpoint_ix,
                    'channel': layer.channel_ix,
                    'zplane': layer.zplane_ix,
                    'level': self.level,
                    'subset_indices': batch
                }
                if self.level == layer.base_level_index:
                    # Only base tiles need to be manipulated, this is then
                    # automatically translated to the subsequent levels
                    description.update({
                        'align': args.align,
                        'illumcorr': args.illumcorr,
                        'clip': args.clip,
                        'clip_value': args.clip_value,
                    })
                job_descriptions['run'].append(description)

            if self.level == layer.base_level_index:
                # Creation of empty base tiles that do not map to an image
                job_count += 1
                job_descriptions['run'].append({
                    'id': job_count,
                    'inputs': {},
                    'outputs': {},
                    'cycle': layer.tpoint_ix,
                    'channel': layer.channel_ix,
                    'zplane': layer.zplane_ix,
                    'level': self.level,
                    'subset_indices': None
                })
        return job_descriptions

    def _build_run_command(self, batch):
        command = super(PyramidBuilder, self)._build_run_command(batch)
        command.extend(['--level', str(batch['level'])])
        return command

    def run_job(self, batch):
        '''
        Create 8-bit greyscale JPEG zoomify pyramid layer of "channel" images.

        Parameters
        ----------
        batch: dict
            job_descriptions element

        See also
        --------
        :py:class:`tmlib.illuminati.layers.ChannelLayer`
        '''
        t = batch['cycle']
        c = batch['channel']
        z = batch['zplane']
        layer = ChannelLayer(
                    self.experiment, tpoint_ix=t, channel_ix=c, zplane_ix=z)

        if self.level == layer.base_level_index:
            logger.info(
                    'create base level pyramid tiles for layer "%s": '
                    'time point %d, channel %d, z-plane %d',
                    layer.name, t, c, z)
            if batch['clip_value'] is None:
                logger.info('use default clip value')
                cycle = self.experiment.plates[0].cycles[t]
                filename = cycle.illumstats_files[c]
                f = os.path.join(cycle.stats_dir, filename)
                with DatasetReader(f) as data:
                    clip_value = data.read('/stats/percentile')
            else:
                clip_value = batch['clip_value']

            if batch['inputs']['image_files']:
                layer.create_base_tiles(
                            clip_value=clip_value,
                            illumcorr=batch['illumcorr'],
                            align=batch['align'],
                            subset_indices=batch['subset_indices'])
            else:
                layer.create_empty_base_tiles(
                            clip_value=clip_value)

        else:
            logger.info(
                    'create level %d pyramid tiles for layer "%s": '
                    'time point %d, channel %d, z-plane %d',
                    self.level, layer.name, t, c, z)
            layer.create_downsampled_tiles(self.level, batch['subset_indices'])

    def collect_job_output(self, batch):
        '''
        Not implemented.
        '''
        raise AttributeError('"%s" object doesn\'t have a "collect_job_output"'
                             ' method' % self.__class__.__name__)

    def apply_statistics(self, output_dir, plates, wells, sites, channels,
                         tpoints, zplanes, **kwargs):
        '''
        Not implemented.
        '''
        raise AttributeError('"%s" object doesn\'t have a "apply_statistics"'
                             ' method' % self.__class__.__name__)
