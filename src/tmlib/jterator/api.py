import os
import sys
import h5py
import shutil
import logging
import numpy as np
import matlab_wrapper as matlab
import collections
from cached_property import cached_property
from . import path_utils
from .project import JtProject
from .join import merge_datasets
from .module import ImageProcessingModule
from .checkers import PipelineChecker
from .. import cfg
from .. import utils
from ..api import ClusterRoutines
from ..errors import PipelineRunError
from ..errors import PipelineDescriptionError
from ..errors import NotSupportedError
from ..writers import Hdf5Writer
from ..readers import Hdf5Reader
from ..logging_utils import map_logging_verbosity

logger = logging.getLogger(__name__)


class ImageAnalysisPipeline(ClusterRoutines):

    '''
    Class for running an image processing pipeline.
    '''

    def __init__(self, experiment, prog_name, verbosity, pipeline,
                 pipe=None, handles=None, **kwargs):
        '''
        Initialize an instance of class ImageAnalysisPipeline.

        Parameters
        ----------
        experiment: tmlib.experiment.Experiment
            configured experiment object
        prog_name: str
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
        they are obtained from the YAML *.pipe* and *.handles* descriptor
        files on disk.

        Raises
        ------
        tmlib.errors.PipelineDescriptionError
            when `pipe` or `handles` are incorrect
        tmlib.errors.PipelineOSError
            when the *.pipe* or *.handles* files do not exist
        '''
        super(ImageAnalysisPipeline, self).__init__(
                experiment, prog_name, verbosity)
        self.experiment = experiment
        self.pipe_name = pipeline
        self.prog_name = prog_name
        self.verbosity = verbosity
        self.project = JtProject(
                    project_dir=self.project_dir, pipe_name=self.pipe_name,
                    pipe=pipe, handles=handles)

    @property
    def project_dir(self):
        '''
        Returns
        -------
        str
            directory where joblist file, pipeline and module descriptor files,
            log output, figures and data will be stored
        '''
        project_dir = os.path.join(
                            self.experiment.dir, 'tmaps',
                            '%s_%s' % (self.prog_name, self.pipe_name))
        return project_dir

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
                project_dir=self.project_dir,
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
        self._figures_dir = os.path.join(self.project_dir, 'figures')
        if not os.path.exists(self._figures_dir):
            os.mkdir(self._figures_dir)
        return self._figures_dir

    @cached_property
    def module_log_dir(self):
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
        module_log_dir = os.path.join(self.project_dir, 'log_modules')
        if not os.path.exists(module_log_dir):
            logger.debug('create directory for module log output: %s'
                         % module_log_dir)
            os.mkdir(module_log_dir)
        return module_log_dir

    def remove_previous_output(self):
        '''
        Remove all figure and module log files.

        Note
        ----
        These files are only produced in the first place when `plot` is set
        to ``True``.
        '''
        shutil.rmtree(self.module_log_dir)
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
        libpath = path_utils.complete_path(libpath, self.project_dir)
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
        self.engines = dict()
        self.engines['Python'] = None
        self.engines['R'] = None
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

    def create_job_descriptions(self, args, job_ids=None):
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
                            '"%s" is not a valid image name' % name)

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

            # TODO: objects from HDF5 files

        else:
            # There might be use cases, where a pipeline doesn't require any
            # input (e.g. for unit tests)
            logger.warning('pipeline doesn\'t describe any input images')
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
                            self.module_log_dir, i+1).values()
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
        command = [self.prog_name]
        command.extend(['-v' for x in xrange(self.verbosity)])
        command.append(self.experiment.dir)
        command.extend(['run', '--job', str(batch['id'])])
        command.extend(['--pipeline', self.pipe_name])
        return command

    def run_job(self, batch):
        '''
        Run pipeline, i.e. execute each module in the order defined by the
        pipeline description. Each job stores its output in a HDF5 file
        with the following structure::

            /metadata                                               # Group
            /metadata/job_id                                        # Dataset {SCALAR}
            /metadata/plate                                         # Dataset {SCALAR}
            /metadata/well_name                                     # Dataset {SCALAR}
            /metadata/well_posistion                                # Group
            /metadata/well_posistion/x                              # Dataset {SCALAR}
            /metadata/well_posistion/y                              # Dataset {SCALAR}
            /metadata/shift_offset                                  # Group
            /metadata/shift_offset/x                                # Dataset {SCALAR}
            /metadata/shift_offset/y                                # Dataset {SCALAR}
            /metadata/image_dimensions                              # Group
            /metadata/image_dimensions/x                            # Dataset {SCALAR}
            /metadata/image_dimensions/y                            # Dataset {SCALAR}
            /objects                                                # Group
            /objects/<object_name>                                  # Group
            /objects/<object_name>/ids                              # Dataset {n}
            /objects/<object_name>/segmentation                     # Group
            /objects/<object_name>/segmentation/parent_name         # Dataset {n}
            /objects/<object_name>/segmentation/object_ids          # Dataset {n}
            /objects/<object_name>/segmentation/is_border           # Dataset {n}
            /objects/<object_name>/segmentation/centroids           # Group
            /objects/<object_name>/segmentation/centroids/y         # Dataset {n}
            /objects/<object_name>/segmentation/centroids/x         # Dataset {n}
            /objects/<object_name>/segmentation/outlines            # Group
            /objects/<object_name>/segmentation/outlines/y          # Dataset {n}
            /objects/<object_name>/segmentation/outlines/x          # Dataset {n}
            /objects/<object_name>/segmentation/image_dimensions    # Group
            /objects/<object_name>/segmentation/image_dimensions/y  # Dataset {n}
            /objects/<object_name>/segmentation/image_dimensions/x  # Dataset {n}
            /objects/<object_name>/features                         # Group
            /objects/<object_name>/features/<feature_name>          # Dataset {n}

        Parameters
        ----------
        batch: dict
            description of the *run* job
        '''
        checker = PipelineChecker(
                project_dir=self.project_dir,
                pipe_description=self.project.pipe['description'],
                handles_descriptions=[
                    h['description'] for h in self.project.handles
                ]
        )
        checker.check_all()
        self._configure_loggers()
        self.start_engines(batch['plot'])
        job_id = batch['id']
        data_file = self.build_data_filename(job_id)
        # Create the HDF5 file (truncate in case it already exists)
        logger.debug('create data file: %s', data_file)
        h5py.File(data_file, 'w').close()

        # Load the images,correct them if requested and align them if required.
        # NOTE: When the experiment was acquired in "multiplexing" mode,
        # images will be aligned automatically. I assume that this is the
        # desired behavior, but one should consider making the alignment
        # optional and give the user the possibility to decide similar to
        # illumination correction.
        images = dict()
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
                orig_dims = img.pixels.dimensions
                img = img.align()
                if not isinstance(img.pixels.array, np.ndarray):
                    raise TypeError(
                            'Jterator requires images as "numpy" arrays. '
                            'Set argument "library" to "numpy".')
                else:
                    pixels_array = img.pixels.array

                # Combine images into "stack"
                if j == 0 and n > 1:
                    dims = img.pixels.dimensions
                    images[ch['name']] = np.empty(
                                            (n, dims[0], dims[1]),
                                            dtype=img.pixels.dtype)
                if n > 1:
                    images[ch['name']][j, :, :] = pixels_array
                else:
                    images[ch['name']] = pixels_array

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
                # All images processed per job were acquired at the same site
                # and thus share the positional metadata information
                with Hdf5Writer(data_file) as data:
                    data.write('/metadata/job_id',
                               data=batch['id'])
                    data.write('/metadata/plate',
                               data=md.plate)
                    data.write('/metadata/well_name',
                               data=md.well_name)
                    data.write('/metadata/well_position/y',
                               data=md.well_position_y)
                    data.write('/metadata/well_position/x',
                               data=md.well_position_x)
                    data.write('/metadata/image_dimensions/y',
                               data=orig_dims[0])
                    data.write('/metadata/image_dimensions/x',
                               data=orig_dims[1])
                    data.write('/metadata/shift_offset/y',
                               data=offset_y)
                    data.write('/metadata/shift_offset/x',
                               data=offset_x)

        # run the pipeline, i.e. execute modules in specified order
        pipeline_data = dict()
        for module in self.pipeline:
            log_files = module.build_log_filenames(
                                self.module_log_dir, job_id)
            inputs = module.prepare_inputs(
                                images=images,
                                upstream_output=pipeline_data,
                                plot=batch['plot'])
            logger.info('run module "%s"', module.name)
            out = module.run(inputs, self.engines[module.language])
            if batch['plot']:
                module.write_output_and_errors(
                    log_files['stdout'], out['stdout'],
                    log_files['stderr'], out['stderr'])
            if not out['success']:
                sys.exit(out['error_message'])
            for key, value in out['pipeline_store'].iteritems():
                # NOTE: In the handles description the mapping
                # of an input/output item has keys "name" and "value".
                # "name" in this context is the formal parameter in the
                # function definition and "value" the argument that is
                # passed to the function.
                # However, for input arguments that are piped between modules
                # "value" specifies the id of the variable (actually the
                # key in the "pipeline_data" dictionary) to which the
                # argument was assigned. Here, the "key" thus
                # corresponds to the value of "value" key of the input item
                # in the handle description.
                # TODO: the whole "mode" and "kind" YAML shit should be
                # mirrored by classes in Python
                kind = [
                    o['kind'] for o in module.description['output']
                    if o['id'] == key
                ][0]
                if kind != 'image':
                    raise NotSupportedError(
                            'Kind "%s" is not supported for outputs '
                            'with mode "pipe"')
                if not isinstance(value, np.ndarray):
                    raise TypeError(
                            'Outputs of kind "pipe" image must have '
                            'type numpy.ndarray')
                pipeline_data[key] = value

            for key, value in out['persistent_store'].iteritems():

                kind = [
                    o['kind'] for o in module.description['output']
                    if o['ref'] == key
                ][0]

                obj = [
                    o['value'] for o in module.description['input']
                    if o['name'] == key
                ][0]

                with Hdf5Writer(data_file) as f:
                    for name, data in value.iteritems():
                        if kind == 'features':
                            group = 'features'
                        elif kind == 'coordinates':
                            group = 'coordinates'
                        elif kind == 'attribute':
                            group = 'attributes'
                        else:
                            # This shouldn't happen after the initial
                            # checks, but safety first :)
                            raise PipelineDescriptionError(
                                    'Unknown kind "%s" for output '
                                    '"%s" of module "%s"'
                                    % (kind, key, module.name))
                        p = 'objects/%s/%s/%s' % (obj, group, name)
                        f.write(p, data)

            if out['figure']:
                if not isinstance(out['figure'], basestring):
                    raise PipelineRunError(
                            'Figure of module "%s" must be '
                            'returned as string.' % module.name)
                figure_file = module.build_figure_filename(
                                    self.figures_dir, job_id)
                module.save_figure(out['figure'], figure_file)

        # TODO: approximate polygons and add global offset to coordinates
        # Refactor tmlib.layer.SegmentedObjectsLayer class

    @utils.notimplemented
    def collect_job_output(self, batch):
        pass

    @utils.notimplemented
    def apply_statistics(self, output_dir, plates, wells, sites, channels,
                         tpoints, zplanes, **kwargs):
        pass
