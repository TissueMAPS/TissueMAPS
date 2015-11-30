import os
import sys
import h5py
import shutil
import logging
import collections
import pandas as pd
import numpy as np
import matlab_wrapper as matlab
from cached_property import cached_property
from . import path_utils
from . import data_fusion
from .project import JtProject
from .module import ImageProcessingModule
from .checkers import PipelineChecker
from .. import utils
from .. import image_utils
from ..api import ClusterRoutines
from ..errors import PipelineDescriptionError
from ..writers import DatasetWriter
from ..readers import DatasetReader
from ..layer import ObjectLayer

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
        libpath = self.project.pipe['description']['project']['lib']
        self._pipeline = list()
        for i, element in enumerate(self.project.pipe['description']['pipeline']):
            if not element['active']:
                continue
            module_path = element['module']
            module_path = path_utils.complete_module_path(
                            module_path, libpath, self.project_dir)
            if not os.path.isabs(module_path):
                module_path = os.path.join(self.project_dir, module_path)
            if not os.path.exists(module_path):
                raise PipelineDescriptionError(
                        'Missing module file: %s' % module_path)
            module_name = self.project.handles[i]['name']
            handles_description = self.project.handles[i]['description']
            module = ImageProcessingModule(
                        name=module_name, module_file=module_path,
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

    def create_job_descriptions(self, args):
        '''
        Create job descriptions for parallel computing.

        Parameters
        ----------
        args: tmlib.metaconfig.args.JteratorInitArgs
            program-specific arguments

        Returns
        -------
        Dict[str, List[dict] or dict]
            job descriptions
        '''
        self.check_pipeline()
        job_descriptions = dict()
        job_descriptions['run'] = list()

        layers = self.project.pipe['description']['images']['layers']
        layer_names = [layer['name'] for layer in layers]

        images = dict()
        for name in layer_names:
            if name is None:
                continue
            images[name] = self.experiment.layer_metadata[name]

        if not images:
            # This is useful for testing purposes, where a pipeline should
            # be run that doesn't require any input
            logger.warning('no layers provided')
            logger.info('create one empty job description')
            job_descriptions['run'] = [{
                'id': 1,
                'inputs': dict(),
                'outputs': dict()
            }]
            return job_descriptions

        batches = [
            {k: v.filenames[i] for k, v in images.iteritems()}
            for i in xrange(len(images.values()[0].filenames))
        ]

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
                    self.build_data_filename(i+1) for i in xrange(len(batches))
                ]
            },
            'outputs': {
                'data_files': [
                    os.path.join(self.experiment.dir,
                                 self.experiment.data_file)
                ]
            },
            'removals': ['data_files']
        }

        return job_descriptions

    def _build_run_command(self, batch):
        # Overwrite method to account for additional "--pipeline" argument
        command = [self.prog_name]
        command.extend(['-v' for x in xrange(self.verbosity)])
        command.extend(['-p', self.pipe_name])
        command.append(self.experiment.dir)
        command.extend(['run', '--job', str(batch['id'])])
        if not self.headless:
            command.append('--plot')
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

        # Load the image and correct/align it if required (requested)
        layer_images = dict()
        layers = self.project.pipe['description']['images']['layers']
        for i, layer in enumerate(layers):
            logger.info('load images of layer "%s"', layer['name'])
            filename = batch['inputs']['image_files'][layer['name']]
            image = self.experiment.get_image_by_name(filename)
            if layer['correct']:
                logger.info('correct images for illumination artifacts')
                for plate in self.experiment.plates:
                    if plate.name != image.metadata.plate_name:
                        continue
                    cycle = plate.cycles[image.metadata.tpoint_ix]
                    stats = cycle.illumstats_images[image.metadata.channel_ix]
                    image = image.correct(stats)
            logger.info('align images between cycles')
            orig_dims = image.pixels.dimensions
            image = image.align()
            if not isinstance(image.pixels, np.ndarray):
                image_array = image_utils.vips_image_to_np_array(
                                                image.pixels.array)
            else:
                image_array = image.pixels.array
            layer_images[layer['name']] = image_array
            # Add some metadata to the HDF5 file, which may be required later
            if i == 0:
                logger.info('add metadata to data file')
                md = image.metadata
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
                    data.write('/metadata/%s/plate_name' % job_id,
                               data=md.plate_name)
                    data.write('/metadata/%s/well_name' % job_id,
                               data=md.well_name)
                    data.write('/metadata/%s/well_pos_x' % job_id,
                               data=md.well_pos_x)
                    data.write('/metadata/%s/well_pos_y' % job_id,
                               data=md.well_pos_y)
                    data.write('/metadata/%s/image_dimension_y' % job_id,
                               data=orig_dims[0])
                    data.write('/metadata/%s/image_dimension_x' % job_id,
                               data=orig_dims[1])
                    data.write('/metadata/%s/shift_offset_y' % job_id,
                               data=offset_y)
                    data.write('/metadata/%s/shift_offset_x' % job_id,
                               data=offset_x)

        outputs = collections.defaultdict(dict)
        outputs['data'] = dict()
        for module in self.pipeline:
            log_files = module.build_log_filenames(self.module_log_dir, job_id)
            figure_file = module.build_figure_filename(self.figures_dir, job_id)
            inputs = module.prepare_inputs(
                        layers=layer_images,
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
        command.extend(['-p', self.pipe_name])
        command.append(self.experiment.dir)
        command.extend(['collect'])
        return command

    def collect_job_output(self, batch):
        '''
        Collect the data stored across individual HDF5 files, fuse them and
        store them in a single, separate HDF5 file.

        Parameters
        ----------
        batch: dict
            job description
        '''
        logger.info('fuse datasets of different jobs into a single data file')
        datasets = data_fusion.fuse_datasets(batch['inputs']['data_files'])
        filename = batch['outputs']['data_files'][0]
        # There could be several pipelines, and each pipeline may only provide
        # some of the data, e.g. one pipeline may provide segmentations, while
        # another may add measurements for the segmented objects.
        # Since it's not possible to delete datasets in an HDF5 file and free
        # the allocated memory. Therefore, a new file will be created temporary
        # to which already existing datasets will be copied. This new, updated
        # file will then subsequently replace the original file.
        def update_datasets(old_file_stream, new_file_stream):
            # Helper function to recursively copy datasets from the "old"
            # file to the "new" file in case the dataset don't already exist.
            def copy_recursively(p):
                groups = old_file_stream.list_groups(p)
                for g in groups:
                    group_path = '{group}/{subgroup}'.format(
                                    group=p, subgroup=g)
                    for d in old_file_stream.list_datasets(group_path):
                        dataset_path = '{group}/{dataset}'.format(
                                            group=group_path, dataset=d)
                        if not new_file_stream.exists(dataset_path):
                            # Keep the more recent dataset.
                            new.write(dataset_path,
                                      old_file_stream.read(dataset_path))
                    copy_recursively(group_path)
            copy_recursively('/')

        tmp_filename = '%s.tmp' % batch['outputs']['data_files'][0]
        with DatasetWriter(tmp_filename) as new:
            for path, data in datasets.iteritems():
                new.write(path, data)
            with DatasetReader(filename) as old:
                update_datasets(old, new)
        
        # Replace the original file with the updated version
        os.remove(filename)
        os.rename(tmp_filename, filename)

        logger.info('remove data files generated by individual jobs')
        # NOTE: In principle, individual files could be removed during data
        # fusion to prevent looping over files twice. However, in case an error
        # occurs during data fusion the files would already be lost and we
        # would have to re-run all jobs. Safety first!
        for k in batch['removals']:
            for f in batch['inputs'][k]:
                logger.debug('remove data file: %s', f)
                # os.remove(f)

        logger.info('calculate object coordinates')
        with DatasetReader(filename) as f:
            objects = f.list_groups('/objects')

        for obj in objects:
            layer = ObjectLayer.create(self.experiment, obj)
            layer.save(filename)

    def apply_statistics(self, output_dir, plates, wells, sites, channels,
                         tpoints, zplanes, **kwargs):
        '''
        Not implemented.
        '''
        raise AttributeError('"%s" object doesn\'t have a "apply_statistics"'
                             ' method' % self.__class__.__name__)
