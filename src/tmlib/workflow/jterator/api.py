import os
import sys
import shutil
import logging
import numpy as np
import matlab_wrapper as matlab
import collections
from cached_property import cached_property
from .project import JtProject
from .module import ImageProcessingModule
from .checkers import PipelineChecker
from .. import cfg
from .. import utils
from . import path_utils
from ..api import ClusterRoutines
from ..errors import PipelineDescriptionError
from ..errors import NotSupportedError
from ..writers import DataTableWriter
from ..logging_utils import map_logging_verbosity

logger = logging.getLogger(__name__)


class ImageAnalysisPipeline(ClusterRoutines):

    '''
    Class for running an image processing pipeline.
    '''

    def __init__(self, experiment, step_name, verbosity, pipeline,
                 pipe=None, handles=None, **kwargs):
        '''
        Initialize an instance of class ImageAnalysisPipeline.

        Parameters
        ----------
        experiment: tmlib.experiment.Experiment
            configured experiment object
        step_name: str
            name of the corresponding program (command line interface)
        verbosity: int
            logging level
        pipeline: str
            name of the pipeline that should be processed
        pipe: dict, optional
            name of the pipeline and the description of module order and
            paths to module code and descriptor files (default: ``None``)
        handles: List[dict], optional
            name of each module and the description of its input/output
            (default: ``None``)
        kwargs: dict, optional
            additional key-value pairs that are ignored

        Note
        ----
        If `pipe` or `handles` are not provided
        they are obtained from the YAML *.pipe* and *.handle* descriptor
        files on disk.
        '''
        super(ImageAnalysisPipeline, self).__init__(
                experiment, step_name, verbosity)
        self.experiment = experiment
        self.pipe_name = pipeline
        self.step_name = step_name
        self.verbosity = verbosity
        self.engines = {'Python': None, 'R': None}
        self.project = JtProject(
                    step_location=self.step_location, pipe_name=self.pipe_name,
                    pipe=pipe, handles=handles)

    @property
    def step_location(self):
        '''
        Returns
        -------
        str
            directory where joblist file, pipeline and module descriptor files,
            log output, figures and data will be stored
        '''
        step_location = os.path.join(
                            self.experiment.dir, 'tmaps',
                            '%s_%s' % (self.step_name, self.pipe_name))
        return step_location

    @property
    def project(self):
        '''
        Returns
        -------
        tmlib.jterator.project.JtProject
            object representation of a jterator project
        '''
        return self._project

    @project.setter
    def project(self, value):
        if not isinstance(value, JtProject):
            raise TypeError('Attribute "project" must have type '
                            'tmlib.jterator.project.JtProject')
        self._project = value

    def check_pipeline(self):
        '''
        Check the content of the `pipe` and `handles` descriptor files.
        '''
        handles_descriptions = [h['description'] for h in self.project.handles]
        checker = PipelineChecker(
                step_location=self.step_location,
                pipe_description=self.project.pipe['description'],
                handles_descriptions=handles_descriptions
        )
        checker.check_all()

    @cached_property
    def figures_dir(self):
        '''
        Returns
        -------
        str
            absolute path to folder containing `.figure` files, containing the
            figure output of each module

        Note
        ----
        Directory is created if it doesn't exist.
        '''
        self._figures_dir = os.path.join(self.step_location, 'figures')
        if not os.path.exists(self._figures_dir):
            os.mkdir(self._figures_dir)
        return self._figures_dir

    @cached_property
    def module_log_location(self):
        '''
        Returns
        -------
        str
            absolute path to the directory with the `.data` HDF5 files,
            containing output data of all modules

        Note
        ----
        Directory is created if it doesn't exist.
        '''
        module_log_location = os.path.join(self.step_location, 'log_modules')
        if not os.path.exists(module_log_location):
            logger.debug('create directory for module log output: %s'
                         % module_log_location)
            os.mkdir(module_log_location)
        return module_log_location

    def remove_previous_output(self):
        '''
        Remove all figure and module log files.

        Note
        ----
        These files are only produced in the first place when `plot` is set
        to ``True``.
        '''
        shutil.rmtree(self.module_log_location)
        shutil.rmtree(self.figures_dir)

    @cached_property
    def pipeline(self):
        '''
        Returns
        -------
        List[tmlib.jterator.module.JtModule]
            pipeline built in modular form based on *pipe* and *handles*
            descriptions

        Raises
        ------
        tmlib.errors.PipelineDescriptionError
            when information in *pipe* description is missing or incorrect
        OSError
            when environment variable "JTLIB" would be required but doesn't
            exist
        '''
        libpath = self.project.pipe['description'].get('lib', None)
        if not libpath:
            if 'JTLIB' in os.environ:
                libpath = os.environ['JTLIB']
            else:
                raise OSError('JTLIB environment variable not set.')
        libpath = path_utils.complete_path(libpath, self.step_location)
        self._pipeline = list()
        for i, element in enumerate(self.project.pipe['description']['pipeline']):
            if not element['active']:
                continue
            module_filename = element['source']
            source_path = path_utils.get_module_path(module_filename, libpath)
            if not os.path.exists(source_path):
                raise PipelineDescriptionError(
                        'Module file does not exist: %s' % source_path)
            name = self.project.handles[i]['name']
            description = self.project.handles[i]['description']
            module = ImageProcessingModule(
                        name=name,
                        source_file=source_path,
                        description=description)
            self._pipeline.append(module)
        if not self._pipeline:
            raise PipelineDescriptionError('No pipeline description available')
        return self._pipeline

    def start_engines(self, plot):
        '''
        Start engines for non-Python modules in the pipeline. We want to
        do this only once, because they may have long startup times, which
        would slow down the execution of the pipeline, if we would have to do
        it repeatedly for each module.

        Parameters
        ----------
        plot: bool
            whether plots should be generated; when ``False`` Matlab will be
            started with the ``"-nojvm"`` option, which will disable plotting
            functionality

        Note
        ----
        For Matlab, you need to set the MATLABPATH environment variable
        in order to add module dependencies to the Matlab path.
        '''
        languages = [m.language for m in self.pipeline]
        if 'Matlab' in languages:
            logger.info('start Matlab engine')
            # NOTE: It is absolutely necessary to specify these startup options
            # for use parallel processing on the cluster. Otherwise some jobs
            # hang up and get killed due to timeout.
            startup_options = '-nosplash -singleCompThread'
            if not plot:
                # Option minimizes memory usage and improves initial startup
                # speed, but disables plotting functionality, so we can only
                # use it in headless mode.
                startup_options += ' -nojvm'
            logger.debug('Matlab startup options: %s', startup_options)
            self.engines['Matlab'] = matlab.MatlabSession(
                                        options=startup_options)
            # We have to make sure that code which may be called by a module,
            # are actually on the MATLAB path.
            # To this end, the MATLABPATH environment variable can be used.
            # However, this only adds the folder specified
            # by the environment variable, but not its subfolders. To enable
            # this, we add each directory specified in the environment variable
            # to the path.
            matlab_path = os.environ['MATLABPATH']
            matlab_path = matlab_path.split(':')
            for p in matlab_path:
                if not p:
                    continue
                self.engines['Matlab'].eval(
                    'addpath(genpath(\'{0}\'));'.format(p)
                )
        # if 'Julia' in languages:
        #     print 'jt - Starting Julia engine'
        #     self.engines['Julia'] = julia.Julia()

    def _configure_loggers(self):
        # TODO: configure loggers for Python, Matlab, and R modules
        jtlogger = logging.getLogger('jtlib')
        level = map_logging_verbosity(self.verbosity)
        jtlogger.setLevel(level)

    def build_data_filename(self, job_id):
        '''
        Build name of the HDF5 file where pipeline data will be stored.

        Parameters
        ----------
        job_id: int
            one-based job identifier number
        '''
        return os.path.join(
                    self.experiment.data_dir,
                    cfg.DATA_NAME_FORMAT.format(s=job_id))

    def create_batches(self, args, job_ids=None):
        '''
        Create job descriptions for parallel computing.

        Parameters
        ----------
        args: tmlib.metaconfig.args.JteratorInitArgs
            step-specific arguments
        job_ids: List[int], optional
            subset of jobs for which descriptions should be generated
            (default: ``None``)

        Returns
        -------
        Dict[str, List[dict] or dict]
            job descriptions
        '''
        self.check_pipeline()
        job_descriptions = dict()
        job_descriptions['run'] = list()

        if 'channels' in self.project.pipe['description']['input'].keys():
            channels = self.project.pipe['description']['input']['channels']
            channel_names = [ch['name'] for ch in channels]

            images_files = collections.defaultdict(list)
            for name in channel_names:
                if name is None:
                    continue
                if name not in self.experiment.channel_names:
                    raise PipelineDescriptionError(
                            '"%s" is not a valid channel name' % name)

                example_cycle = self.experiment.plates[0].cycles[0]
                n_zplanes = len(np.unique(example_cycle.image_metadata.zplane))
                n_tpoints = len(np.unique(example_cycle.image_metadata.tpoint))
                if n_tpoints > 1 and n_zplanes > 1:
                    raise NotSupportedError(
                            'Jterator cannot load 4D images (yet).')

                layer_names = self.experiment.channel_metadata[name].layers
                for layer in layer_names:
                    images_files[name].append(
                            self.experiment.layer_metadata[layer].filenames
                    )

            # TODO: objects

        else:
            # There might be use cases, where a pipeline doesn't require any
            # input (e.g. for unit tests)
            logger.warning('pipeline doesn\'t describe any inputs')
            logger.info('create a single empty job description')
            images_files = collections.defaultdict(list)

        if images_files:
            batches = [
                collections.defaultdict(list)
                for i in xrange(len(images_files.values()[0][0]))
            ]
            for k, v in images_files.iteritems():
                for i in xrange(len(v[0])):
                    for j in xrange(len(v)):
                        batches[i][k].append(v[j][i])

            job_descriptions['run'] = [{
                'id': i+1,
                'inputs': {
                    'image_files': batch
                },
                'outputs': {
                    'data_files': [self.build_data_filename(i+1)],
                    'figure_files': [
                        module.build_figure_filename(
                            self.figures_dir, i+1)
                        for module in self.pipeline
                    ],
                    'log_files': utils.flatten([
                        module.build_log_filenames(
                            self.module_log_location, i+1).values()
                        for module in self.pipeline
                    ])
                },
                'plot': args.plot
            } for i, batch in enumerate(batches)]

            if job_ids:
                job_descriptions_subset = dict()
                job_descriptions_subset['run'] = list()
                for j in job_ids:
                    job_descriptions_subset['run'].append(
                        job_descriptions['run'][j-1]  # job IDs are one-based
                    )
                return job_descriptions_subset
            else:
                return job_descriptions

        else:
            job_descriptions['run'] = [{
                'id': 1,
                'inputs': dict(),
                'outputs': dict(),
                'plot': False
            }]
            return job_descriptions

    def _build_run_command(self, batch):
        # Overwrite method to account for additional "---pipeline" argument
        command = [self.step_name]
        command.extend(['-v' for x in xrange(self.verbosity)])
        command.append(self.experiment.dir)
        command.extend(['run', '--job', str(batch['id'])])
        command.extend(['--pipeline', self.pipe_name])
        return command

    def run_job(self, batch):
        '''
        Run pipeline, i.e. execute each module in the order defined by the
        pipeline description.

        Parameters
        ----------
        batch: dict
            description of the *run* job
        '''
        checker = PipelineChecker(
                step_location=self.step_location,
                pipe_description=self.project.pipe['description'],
                handles_descriptions=[
                    h['description'] for h in self.project.handles
                ]
        )
        checker.check_all()
        self._configure_loggers()
        self.start_engines(batch['plot'])
        job_id = batch['id']
        data_file = batch['outputs']['data_files'][0]
        with DataTableWriter(data_file, truncate=True) as writer:
            logger.debug('data is stored in file "%s"', data_file)

        # Load the images,correct them if requested and align them if required.
        # NOTE: When the experiment was acquired in "multiplexing" mode,
        # images will be aligned automatically. I assume that this is the
        # desired behavior, but one should consider making the alignment
        # optional and give the user the possibility to decide similar to
        # illumination correction.
        store = {
            'pipe': dict(),
            'figures': list(),
            'objects': dict(),
            'channels': list()
        }
        channels = self.project.pipe['description']['input']['channels']
        # TODO: objects
        for i, ch in enumerate(channels):
            logger.info('load images of channel "%s"', ch['name'])
            filenames = batch['inputs']['image_files'][ch['name']]
            n = len(filenames)
            for j in xrange(n):
                name = os.path.basename(filenames[j])
                img = self.experiment.get_image_by_name(name)
                if ch['correct']:
                    logger.info('correct images for illumination artifacts')
                    for plate in self.experiment.plates:
                        if plate.index != img.metadata.plate:
                            continue
                        cycle = plate.cycles[img.metadata.cycle]
                        stats = cycle.illumstats_images[img.metadata.channel]
                        stats.smooth_stats()
                        img = img.correct(stats)
                logger.info('align images between cycles')
                orig_dims = img.dimensions
                img = img.align()
                pixels_array = img.pixels

                # Combine images into "stack"
                if j == 0 and n > 1:
                    dims = img.dimensions
                    store['pipe'][ch['name']] = np.empty(
                                            (n, dims[0], dims[1]),
                                            dtype=img.dtype)
                if n > 1:
                    store['pipe'][ch['name']][j, :, :] = pixels_array
                else:
                    store['pipe'][ch['name']] = pixels_array
                store['channels'].append(ch['name'])

            # Add some metadata to the HDF5 file, which may be required later
            if i == 0:
                logger.info('add metadata to data file')
                md = img.metadata
                shift_y = md.upper_overhang - md.y_shift
                if shift_y < 0:
                    offset_y = abs(shift_y)
                else:
                    offset_y = 0
                shift_x = md.left_overhang - md.x_shift
                if shift_x < 0:
                    offset_x = abs(shift_x)
                else:
                    offset_x = 0

        # Run modules
        for i, module in enumerate(self.pipeline):
            logger.info('run module "%s"', module.name)
            module.update_handles(store, batch['plot'])
            output = module.run(self.engines[module.language])

            log_files = module.build_log_filenames(
                                self.module_log_location, job_id)
            module.write_output_and_errors(
                log_files['stdout'], output['stdout'],
                log_files['stderr'], output['stderr'])

            if not output['success']:
                sys.exit(output['error_message'])

            store = module.update_store(store)

        # 

    @utils.notimplemented
    def collect_job_output(self, batch):
        pass

    @utils.notimplemented
    def apply_statistics(self, output_dir, plates, wells, sites, channels,
                         tpoints, zplanes, **kwargs):
        pass
