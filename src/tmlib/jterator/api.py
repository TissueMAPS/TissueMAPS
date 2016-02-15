import os
import sys
import h5py
import shutil
import logging
import collections
import numpy as np
import matlab_wrapper as matlab
from collections import defaultdict
from cached_property import cached_property
from . import path_utils
from .project import JtProject
from .module import ImageProcessingModule
from .checkers import PipelineChecker
from .. import utils
from ..api import ClusterRoutines
from ..errors import PipelineDescriptionError
from ..errors import NotSupportedError
from ..writers import DatasetWriter
from ..readers import DatasetReader
from ..layer import SegmentedObjectLayer
from ..layer import WellObjectLayer

logger = logging.getLogger(__name__)


class ImageAnalysisPipeline(ClusterRoutines):

    '''
    Class for running an image processing pipeline.
    '''

    def __init__(self, experiment, prog_name, verbosity, pipe_name,
                 pipe=None, handles=None, headless=True):
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
        pipe_name: str
            name of the pipeline that should be processed
        pipe: dict, optional
            name of the pipeline and the description of module order and
            paths to module code and descriptor files (default: ``None``)
        handles: List[dict], optional
            name of each module and the description of its input/output
            (default: ``None``)
        headless: bool, optional
            whether plotting should be disabled (default: ``True``)

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
        self.pipe_name = pipe_name
        self.prog_name = prog_name
        self.verbosity = verbosity
        self.headless = headless
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
    def data_dir(self):
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
        self._data_dir = os.path.join(self.project_dir, 'data')
        if not os.path.exists(self._data_dir):
                os.mkdir(self._data_dir)
        return self._data_dir

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
        These files are only produced in the first place when `headless` is set
        to ``False``.
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
        '''
        if self.project.pipe['description']['project']['lib']:
            libpath = self.project.pipe['description']['project']['lib']
            libpath = path_utils.complete_path(
                            self.libpath, self.project_dir)
        else:
            if 'JTLIB' in os.environ:
                libpath = os.environ['JTLIB']
            else:
                raise ValueError('JTLIB environment variable not set.')
        self._pipeline = list()
        for i, element in enumerate(self.project.pipe['description']['pipeline']):
            if not element['active']:
                continue
            module_filename = element['module']
            module_path = path_utils.get_module_path(module_filename, libpath)
            if not os.path.exists(module_path):
                raise PipelineDescriptionError(
                        'Module file does not exist: %s' % module_path)
            module_name = self.project.handles[i]['name']
            handles_description = self.project.handles[i]['description']
            module = ImageProcessingModule(
                        name=module_name,
                        module_file=module_path,
                        handles_description=handles_description)
            self._pipeline.append(module)
        if not self._pipeline:
            raise PipelineDescriptionError('No pipeline description available')
        return self._pipeline

    def start_engines(self):
        '''
        Start engines for non-Python modules in the pipeline. We want to
        do this only once, because they may have long startup times, which
        would slow down the execution of the pipeline, if we would have to do
        it repeatedly for each module.

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
            # TODO: Add a random delay before starting MATLAB session to
            # avoid to many concomitant license calls
            # time.sleep(random.randint(10))
            self.engines['Matlab'] = matlab.MatlabSession()
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
                self.engines['Matlab'].eval('addpath(genpath(\'{0}\'));'.format(p))
        # if 'Julia' in languages:
        #     print 'jt - Starting Julia engine'
        #     self.engines['Julia'] = julia.Julia()

    def configure_loggers(self):
        # TODO: configure loggers for Python, Matlab, and R modules
        pass

    def build_data_filename(self, job_id):
        '''
        Build name of the HDF5 file where pipeline data will be stored.

        Parameters
        ----------
        job_id: int
            one-based job identifier number
        '''
        data_file = os.path.join(self.data_dir,
                                 '%s_%.5d.data.h5' % (self.pipe_name, job_id))
        return data_file

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

        # TODO: make this more general for 3D time series datasets

        if 'planes' in self.project.pipe['description']['images']:

            # Generate a 2D array

            planes = self.project.pipe['description']['images']['planes']
            plane_names = [item['name'] for item in planes]

            valid_names = self.experiment.layer_names.values()

            images = dict()
            for name in plane_names:
                if name is None:
                    continue
                if name not in valid_names:
                    raise PipelineDescriptionError(
                            '"%s" is not a valid image name' % name)
                # Warp into a list of length 1 to be compatible with the
                # other image loading modes, where several planes are
                # loaded into a 3-dimensional "stack" or "series".
                images[name] = [self.experiment.layer_metadata[name].filenames]

            # if not images:
            #     # This is useful for testing purposes, where a pipeline should
            #     # be run that doesn't require any input
            #     logger.warning('no planes provided')
            #     logger.info('create one empty job description')
            #     job_descriptions['run'] = [{
            #         'id': 1,
            #         'inputs': dict(),
            #         'outputs': dict()
            #     }]
            #     return job_descriptions

        elif 'stacks' in self.project.pipe['description']['images']:

            # Generate a 3D array:
            # A "stack" is a group of planes acquired at the same site, but at
            # different z-resolutions

            example_cycle = self.experiment.plates[0].cycles[0]
            n_zplanes = len(np.unique(example_cycle.image_metadata.zplane_ix))
            if n_zplanes == 1:
                raise PipelineDescriptionError(
                        'A "stack" can only be generated for 3D datasets.')
            n_tpoints = len(np.unique(example_cycle.image_metadata.tpoint_ix))
            mode = self.experiment.user_cfg.acquisition_mode
            # Works fine in "multiplexing", because each time point maps to
            # a different visual. This is not the case for "series" data.
            if n_tpoints > 0 and mode == 'series':
                raise NotSupportedError(
                        'Generation of "stacks" is not supported for '
                        '3D time series datasets.')

            stacks = self.project.pipe['description']['images']['stacks']
            stack_names = [item['name'] for item in stacks]

            valid_names = self.experiment.visual_names

            images = defaultdict(list)
            for name in stack_names:
                if name is None:
                    continue
                if name not in valid_names:
                    raise PipelineDescriptionError(
                            '"%s" is not a valid image name' % name)
                layer_names = self.experiment.visual_layers_map[name]
                for l_name in layer_names:
                    # List of length n, where n is number of z--pipelinelanes
                    images[name].append(
                        self.experiment.layer_metadata[l_name].filenames
                    )

        elif 'series' in self.project.pipe['description']['images']:

            # Generate a 3D array:
            # A "series" is a group of planes acquired at the same site,
            # but at different time points.

            example_cycle = self.experiment.plates[0].cycles[0]
            n_tpoints = len(np.unique(example_cycle.image_metadata.tpoint_ix))
            if n_tpoints == 1:
                raise PipelineDescriptionError(
                        'A "series" can only be generated for datasets '
                        'with multiple time points')
            n_zplanes = len(np.unique(example_cycle.image_metadata.zplane_ix))
            if n_zplanes > 0:
                raise NotSupportedError(
                        'Generation of "series" is not supported for '
                        '3D datasets.')

            series = self.project.pipe['description']['images']['stacks']
            series_names = [item['name'] for item in series]

            valid_names = self.experiment.visual_names

            images = defaultdict(list)
            for name in series_names:
                if name is None:
                    continue
                if name not in valid_names:
                    raise PipelineDescriptionError(
                            '"%s" is not a valid image name' % name)
                layer_names = self.experiment.visual_layers_map[name]
                for l_name in layer_names:
                    # List of length n, where n is number of time points
                    images[name].append(
                        self.experiment.layer_metadata[l_name].filenames
                    )

        else:
            raise ValueError(
                    'Images can be loaded as "planes", "stacks", or "series"')

        batches = [defaultdict(list) for i in xrange(len(images.values()[0][0]))]
        for k, v in images.iteritems():
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
            }
        } for i, batch in enumerate(batches)]

        job_descriptions['collect'] = {
            'inputs': {
                'data_files': [
                    self.build_data_filename(i+1)
                    for i in xrange(len(batches))
                ]
            },
            'outputs': {
                'data_files': [
                    os.path.join(self.experiment.dir,
                                 self.experiment.data_file)
                ]
            },
            'removals': [
                'data_files'
            ],
            'merge': args.merge,
            'align': True  # TODO: should become an argument
        }

        if job_ids:
            job_description_subset = dict()
            job_description_subset['run'] = list()
            for j in job_ids:
                job_description_subset['run'].append(
                    job_descriptions['run'][j-1]  # job IDs are one-based
                )
            return job_description_subset
        else:
            return job_descriptions

    def _build_run_command(self, batch):
        # Overwrite method to account for additional "---pipelineipeline" argument
        command = [self.prog_name]
        command.extend(['-v' for x in xrange(self.verbosity)])
        command.append(self.experiment.dir)
        command.extend(['run', '--job', str(batch['id'])])
        command.extend(['--pipeline', self.pipe_name])
        if not self.headless:
            command.append('---pipelinelot')
        return command

    def run_job(self, batch):
        '''
        Run pipeline, i.e. execute each module in the order defined by the
        pipeline description. Each job stores its output in a HDF5 file
        with the following structure::

            /metadata                                               # Group
            /metadata/job_id                                        # Dataset {SCALAR}
            /metadata/plate_name                                    # Dataset {SCALAR}
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
        self.start_engines()
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
        if 'planes' in self.project.pipe['description']['images']:
            collection = self.project.pipe['description']['images']['planes']
            item_type = 'plane'
        elif 'stacks' in self.project.pipe['description']['images']:
            collection = self.project.pipe['description']['images']['stacks']
            item_type = 'stack'
        elif 'series' in self.project.pipe['description']['images']:
            collection = self.project.pipe['description']['images']['series']
            item_type = 'series'
        for i, item in enumerate(collection):
            logger.info('load images of %s "%s"', item_type, item['name'])
            filenames = batch['inputs']['image_files'][item['name']]
            n = len(filenames)
            for j in xrange(n):
                name = os.path.basename(filenames[j])
                img = self.experiment.get_image_by_name(name)
                if item['correct']:
                    logger.info('correct images for illumination artifacts')
                    for plate in self.experiment.plates:
                        if plate.name != img.metadata.plate_name:
                            continue
                        cycle = plate.cycles[img.metadata.tpoint_ix]
                        stats = cycle.illumstats_images[img.metadata.channel_ix]
                        img = img.correct(stats)
                logger.info('align images between cycles')
                orig_dims = img.pixels.dimensions
                img = img.align()
                if not isinstance(img.pixels.array, np.ndarray):
                    # pixels_array = vips_image_to_np_array(image.pixels.array)
                    raise TypeError(
                            'Jterator requires images as "numpy" arrays. '
                            'Set "library" to "numpy".')
                else:
                    pixels_array = img.pixels.array

                # Combine images into 3D "stack" or "series" array
                if j == 0 and n > 1:
                    dims = img.pixels.dimensions
                    images[item['name']] = np.empty((n, dims[0], dims[1]),
                                                    dtype=img.pixels.dtype)
                if n > 1:
                    images[item['name']][j, :, :] = pixels_array
                else:
                    images[item['name']] = pixels_array

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
                with DatasetWriter(data_file) as data:
                    data.write('/metadata/job_id',
                               data=batch['id'])
                    data.write('/metadata/plate_name',
                               data=md.plate_name)
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

        outputs = collections.defaultdict(dict)
        outputs['data'] = dict()
        for module in self.pipeline:
            log_files = module.build_log_filenames(
                                self.module_log_dir, job_id)
            figure_file = module.build_figure_filename(
                                self.figures_dir, job_id)
            inputs = module.prepare_inputs(
                                images=images,
                                upstream_output=outputs['data'],
                                data_file=data_file, figure_file=figure_file,
                                job_id=job_id,
                                experiment_dir=self.experiment.dir,
                                headless=self.headless)
            logger.info('run module "%s"', module.name)
            logger.debug('module file: %s', module.module_file)
            out = module.run(inputs, self.engines[module.language])
            if not self.headless:
                # The output is also included in log report of the job.
                # It is mainly used for setting up a pipeline in the GUI.
                module.write_output_and_errors(
                    log_files['stdout'], out['stdout'],
                    log_files['stderr'], out['stderr'])
            if not out['success']:
                sys.exit(out['error_message'])
            for k, v in out.iteritems():
                if k == 'data':
                    outputs['data'].update(out[k])
                else:
                    outputs[k][module.name] = out[k]

    def _build_collect_command(self):
        command = [self.prog_name]
        command.extend(['-v' for x in xrange(self.verbosity)])
        command.append(self.experiment.dir)
        command.append('collect')
        command.extend(['--pipeline', self.pipe_name])
        return command

    def collect_job_output(self, batch):
        '''
        Collect the data stored across individual HDF5 files, fuse, and store
        them in a single HDF5 file.

        The final file has the following hierarchical structure::

            /objects/<object_name>/features                         # Dataset {n, p}
            /objects/<object_name>/map_data                         # Group
            /objects/<object_name>/map_data/coordinates             # Group
            /objects/<object_name>/map_data/coordinates/<object_id> # Dataset {m, 2}

        where *n* is the total number of objects, *p* is the number of
        features that were extracted for each object, and
        *m* are the number of outline coordinates for each object
        (*m* differs between object entities).

        Parameters
        ----------
        batch: dict
            job description
        '''
        # TODO: structure of HDF5 file:
        # PerformanceWarning: group ``/objects/nuclei/map_data/coordinates``
        # is exceeding the recommended maximum number of children (16384);
        # be ready to see PyTables asking for *lots* of memory and possibly slow I/O.

        example_file = batch['inputs']['data_files'][0]
        with DatasetReader(example_file) as f:
            objects = f.list_groups('/objects')

        for obj in objects:
            logger.info('create layer for segmented objects "%s"', obj)
            layer = SegmentedObjectLayer(self.experiment, obj)
            layer.create(batch['inputs']['data_files'], align=batch['align'])

        logger.info('create layer for objects "wells"')
        well_layer = WellObjectLayer(self.experiment)
        well_layer.create()

    def apply_statistics(self, output_dir, plates, wells, sites, channels,
                         tpoints, zplanes, **kwargs):
        '''
        Not implemented.
        '''
        raise AttributeError('"%s" object doesn\'t have a "apply_statistics"'
                             ' method' % self.__class__.__name__)
