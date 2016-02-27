import os
import logging
import numpy as np
from cached_property import cached_property
from collections import defaultdict
from gc3libs.quantity import Duration
from gc3libs.quantity import Memory
from ..layer import ChannelLayer
from ..readers import DatasetReader
from ..api import ClusterRoutines
from ..jobs import RunJob
from ..jobs import RunJobCollection
from ..jobs import MultiRunJobCollection
from ..jobs import CollectJob
from ..tmaps.workflow import WorkflowStep

logger = logging.getLogger(__name__)


class PyramidBuilder(ClusterRoutines):

    def __init__(self, experiment, prog_name, verbosity, **kwargs):
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
        kwargs: dict
            mapping of additional key-value pairs that are ignored
        '''
        super(PyramidBuilder, self).__init__(
                experiment, prog_name, verbosity)

    @cached_property
    def project_dir(self):
        '''
        Returns
        -------
        str
            directory where *.job* files and log output will be stored
        '''
        project_dir = os.path.join(
                            self.experiment.dir, 'tmaps', self.prog_name)
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
        for identifier in self.experiment.layer_names.keys():
            layer = ChannelLayer(
                            self.experiment,
                            tpoint_ix=identifier[0],
                            channel_ix=identifier[1],
                            zplane_ix=identifier[2]
            )
            for index, level in enumerate(reversed(range(layer.n_zoom_levels))):
                # NOTE: The pyramid "level" increases from top to bottom.
                # We build the pyramid bottom-up, therefore, the "index"
                # decreases from top to bottom.
                if level == layer.base_level_index:
                    layer.create_tile_groups()
                    layer.create_image_properties_file()
                    batches = self._create_batches(
                                    range(len(layer.metadata.filenames)),
                                    args.batch_size)
                else:
                    # Adjust the batch size for subsequent levels
                    level_batch_size = args.batch_size * 10 * level
                    batches = self._create_batches(
                                    range(len(layer.tile_files[level])),
                                    level_batch_size)

                for batch in batches:
                    job_count += 1
                    # NOTE: For the highest resolution level, the input files are
                    # the original microscope images. For all other levels,
                    # the input files are the tiles of the next higher resolution
                    # level (the ones created in the prior run).
                    # For consistency, the paths to both types of image files
                    # are provided relative to the root pyramid directory.
                    if level == layer.base_level_index:
                        filenames = layer.metadata.filenames
                        filenames = list(np.array(filenames)[batch])
                        input_files = [
                            os.path.relpath(f, layer.dir)
                            for f in filenames
                        ]
                        # tile_mapping = layer.base_tile_mappings['image_to_tiles']
                        # output_files = [
                        #     layer.tile_files[level][c]
                        #     for f in input_files
                        #     for c in tile_mapping[os.path.basename(f)]
                        # ]
                    else:
                        input_files = []
                    # else:
                    #     output_files = layer.tile_files[level].values()
                    #     output_files = list(np.array(output_files)[batch])
                    #     input_files = [
                    #         layer.tile_files[level + 1][c]
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
                        'level': level,
                        'index': index,
                        'subset_indices': batch
                    }
                    if level == layer.base_level_index:
                        # Only base tiles need to be corrected for illumination
                        # artifacts and aligned, this then automatically
                        # translates to the subsequent levels
                        description.update({
                            'align': args.align,
                            'illumcorr': args.illumcorr,
                            'clip': args.clip,
                            'clip_value': args.clip_value,
                        })
                    job_descriptions['run'].append(description)

                if level == layer.base_level_index:
                    # Creation of empty base tiles that do not map to an image
                    job_count += 1
                    job_descriptions['run'].append({
                        'id': job_count,
                        'inputs': {},
                        'outputs': {},
                        'cycle': layer.tpoint_ix,
                        'channel': layer.channel_ix,
                        'zplane': layer.zplane_ix,
                        'level': level,
                        'index': index,
                        'clip_value': None,
                        'subset_indices': None
                    })
        return job_descriptions

    def create_jobs(self, job_descriptions,
                    duration=None, memory=None, cores=None):
        '''
        Create jobs that can be submitted for processing.

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

        if 'run' in job_descriptions.keys():
            logger.info('create jobs for "run" phase')
            multi_run_jobs = defaultdict(list)
            for i, batch in enumerate(job_descriptions['run']):

                job = RunJob(
                        step_name=self.prog_name,
                        arguments=self._build_run_command(batch),
                        output_dir=self.log_dir,
                        job_id=batch['id'],
                        index=batch['index']
                )
                if duration:
                    job.requested_walltime = Duration(duration)
                if memory:
                    job.requested_memory = Memory(memory, Memory.GB)
                if cores:
                    if not isinstance(cores, int):
                        raise TypeError('Argument "cores" must have type int.')
                    if not cores > 0:
                        raise ValueError('The value of "cores" must be positive.')
                    job.requested_cores = cores

                multi_run_jobs[batch['index']].append(job)

            run_jobs = MultiRunJobCollection(self.prog_name)
            for index, jobs in multi_run_jobs.iteritems():
                run_jobs.add(
                    RunJobCollection(self.prog_name, jobs, index=index))

        else:
            run_jobs = None

        if 'collect' in job_descriptions.keys():
            logger.info('create job for "collect" phase')
            batch = job_descriptions['collect']

            collect_job = CollectJob(
                    step_name=self.prog_name,
                    arguments=self._build_collect_command(),
                    output_dir=self.log_dir
            )
            collect_job.requested_walltime = Duration('01:00:00')
            collect_job.requested_memory = Memory(4, Memory.GB)

        else:
            collect_job = None

        jobs = WorkflowStep(
                    name=self.prog_name,
                    run_jobs=run_jobs,
                    collect_job=collect_job
        )

        return jobs

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
        layer = ChannelLayer(
                    self.experiment,
                    tpoint_ix=batch['cycle'],
                    channel_ix=batch['channel'],
                    zplane_ix=batch['zplane'])

        if batch['level'] == layer.base_level_index:
            logger.info(
                    'create base level pyramid tiles for layer "%s": '
                    'cycle %d, channel %d, z-plane %d',
                    layer.name,
                    batch['cycle'], batch['cycle'], batch['zplane'])
            if batch['clip_value'] is None:
                logger.info('use default clip value')
                cycle = self.experiment.plates[0].cycles[batch['cycle']]
                filename = cycle.illumstats_files[batch['channel']]
                f = os.path.join(cycle.stats_dir, filename)
                with DatasetReader(f) as data:
                    clip_value = data.read('/stats/percentile')
            else:
                clip_value = batch['clip_value']

            if batch['inputs']:
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
                    'cycle %d, channel %d, z-plane %d',
                    batch['level'], layer.name,
                    batch['cycle'], batch['cycle'], batch['zplane'])
            layer.create_downsampled_tiles(
                    batch['level'], batch['subset_indices'])

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
