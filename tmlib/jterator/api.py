import os
import sys
import h5py
import collections
import matlab_wrapper as matlab
from cached_property import cached_property
from . import pathutils
from .project import JtProject
from .module import ImageProcessingModule
from .checker import PipelineChecker
from .. import utils
from ..cluster import ClusterRoutines
from ..errors import PipelineDescriptionError
from ..errors import PipelineOSError


class ImageProcessingPipeline(ClusterRoutines):

    '''
    Class for running a Jterator image processing pipeline.
    '''

    def __init__(self, experiment, pipe_name, prog_name,
                 pipe=None, handles=None,
                 logging_level='critical'):
        '''
        Initialize an instance of class ImageProcessingPipeline.

        Parameters
        ----------
        experiment: Experiment
            experiment object that holds information about the content of the
            experiment directory
        pipe_name: str
            name of the pipeline that is being processed
        prog_name: str
            name of the corresponding program (command line interface)
        pipe: dict, optional
            name of the pipeline and the description of module order and
            paths to module code and descriptor files
        handles: List[dict], optional
            name of each module and the description of its input/output
        logging_level: str, optional
            configuration of GC3Pie logger; either "debug", "info", "warning",
            "error" or "critical" (defaults to ``"critical"``)

        Note
        ----
        If `pipe` or `handles` are not provided
        they are obtained from the YAML *.pipe* and *.handles* descriptor
        files on disk.

        Raises
        ------
        PipelineDescriptionError
            when `pipe` or `handles` are incorrect
        PipelineOSError
            when the *.pipe* or *.handles* files do not exist

        See also
        --------
        `tmlib.cfg`_
        '''
        super(ImageProcessingPipeline, self).__init__(
            experiment, prog_name, logging_level)
        self.experiment = experiment
        self.pipe_name = pipe_name
        self.prog_name = prog_name
        self._pipe = pipe
        self._handles = handles

    @cached_property
    def project_dir(self):
        '''
        Returns
        -------
        str
            directory where joblist file, pipeline and module descriptor files,
            log output, figures and data will be stored
        '''
        self._project_dir = os.path.join(self.experiment.dir,
                                         'tm_%s_%s' % (self.prog_name,
                                                       self.pipe_name))
        return self._project_dir

    @property
    def pipe(self):
        '''
        Returns
        -------
        dict or None
            name of the pipeline and the description of module order and
            paths to module code and descriptor files (returns ``None`` if a
            pipeline description is neither provided nor available from file
            on disk)
        '''
        if self._pipe is None:
            try:
                self._pipe = dict()
                self._pipe['description'] = self._read_pipe_file()
                self._pipe['name'] = self.pipe_name
            except OSError:
                self._pipe = None
        return self._pipe

    @property
    def handles(self):
        '''
        Returns
        -------
        List[dict]
            name of each module and the description of its input/output

        Raises
        ------
        PipelineOSError
            when a handles file does not exist
        '''
        if self._handles is None:
            if self.pipe is None:
                self._handles = None
            else:
                self._handles = list()
                for element in self.pipe['description']['pipeline']:
                    handles_file = element.handles
                    if not os.path.isabs(handles_file):
                        handles_file = os.path.join(self.project_dir,
                                                    handles_file)
                    if not os.path.exists(handles_file):
                        raise PipelineOSError(
                                'Handles file does not exist: "%s"'
                                % handles_file)
                    handles_description = dict()
                    handles_description['description'] = \
                        self._read_handles_file(handles_file)
                    handles_description['name'] = \
                        os.path.splitext(os.path.basename(handles_file))[0]
                    self._handles.append(handles_description)
        return self._handles

    def create_project(self, repo_dir=None, skel_dir=None):
        '''
        Create a project on disk.

        Parameters
        ----------
        repo_dir: str, optional
            path to a repository location that contains the module files
        skel_dir: str
            path to a repository location that contains *.pipe* and
            *.handles* file templates for standard image analysis routines

        See also
        --------
        `tmlib.jterator.project.JtProject`_
        '''
        project = JtProject(
                    project_dir=self.project_dir, pipe_name=self.pipe_name,
                    pipe=self.pipe, handles=self.handles)
        project.create(repo_dir, skel_dir)

    def check_pipeline(self):
        try:
            self.pipe
        except OSError:
            raise PipelineOSError('Pipe file does not exist.')
        checker = PipelineChecker(
                    project_dir=self.project_dir,
                    pipe=self.pipe, handles=self.handles)
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
        Creates the directory if it doesn't exist.
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
        Creates the directory if it doesn't exist.
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
        Creates the directory if it doesn't exist.
        '''
        self._module_log_dir = os.path.join(self.project_dir, 'log_modules')
        if not os.path.exists(self._module_log_dir):
                os.mkdir(self._module_log_dir)
        return self._module_log_dir

    @property
    def pipe_file(self):
        '''
        Returns
        -------
        str
            absolute path to the *.pipe* YAML pipeline descriptor file
        '''
        self._pipeline_file = os.path.join(self.project_dir,
                                           '%s.pipe' % self.pipe_name)
        return self._pipeline_file

    def _read_pipe_file(self):
        content = utils.read_yaml(self.pipe_file)
        # Make paths absolute
        content['project']['libpath'] = pathutils.complete_path(
                    content['project']['libpath'], self.project_dir)
        content['jobs']['folder'] = pathutils.complete_path(
                    content['jobs']['folder'], self.project_dir)
        return content

    @cached_property
    def pipeline(self):
        '''
        Returns
        -------
        List[JtModule]
            pipeline built in modular form based on *pipe* and *handles*
            descriptions

        Raises
        ------
        PipelineDescriptionError
            when information in *pipe* description is missing or incorrect
        '''
        libpath = self.pipe['project']['libpath']
        self._modules = list()
        for i, element in self.pipe['pipeline']:
            if not element['active']:
                continue
            module_path = element['module']
            module_path = pathutils.complete_module_path(
                            module_path, libpath, self.project_dir)
            if not os.path.isabs(module_path):
                module_path = os.path.join(self.project_dir, module_path)
            if not os.path.exists(module_path):
                raise PipelineDescriptionError(
                        'Missing module file: %s' % module_path)
                module_name = self.handles[i]['name']
            handles_description = self.handles[i]['description']
            module = ImageProcessingModule(
                        name=module_name, module_file=module_path,
                        handles_description=handles_description,
                        project_dir=self.project_dir,
                        logging_level=self.logging_level,
                        headless=self.headless)
            self._modules.append(module)
        if not self._modules:
            raise PipelineDescriptionError(
                        'No pipeline description: "%s"' % self.pipe_filename)
        return self._modules

    def start_engines(self):
        '''
        Start engines for non-Python modules in the pipeline. We want to
        do this only once, because they may have long startup times, which
        would slow down the execution of the pipeline, if we would have to do
        it repeatedly for each module.
        '''
        languages = [m.language for m in self.modules]
        self.engines = dict()
        self.engines['Python'] = None
        self.engines['R'] = None
        if 'Matlab' in languages:
            self.engines['Matlab'] = matlab.MatlabSession()
            # We have to make sure code that may be called within the module,
            # i.e. the module dependencies, are actually on the path.
            # To this end, can make use of the MATLABPATH environment variable.
            # However, this only adds the folder specified
            # by the environment variable, but not its subfolders. To enable
            # this we generate a Matlab path for each directory specified
            # in the environment variable.
            matlab_path = os.environ['MATLABPATH']
            matlab_path = matlab_path.split(':')
            for p in matlab_path:
                if not p:
                    continue
                self.engines['Matlab'].eval('addpath(genpath(\'{0}\'));'.format(p))
        # if 'Julia' in languages:
        #     print 'jt - Starting Julia engine'
        #     self.engines['Julia'] = julia.Julia()

    def create_data_file(self, job_id):
        '''
        Create an HDF5 file on disk for storage of data of the current job.

        Parameters
        ----------
        job_id: int
            one-based job identifier number

        Returns
        -------
        str
            name of the `.data` HDF5 file
        '''
        data_file = os.path.join(self.data_dir,
                                 '%s_%.5d.data' % (self.pipe_name, job_id))
        h5py.File(data_file, 'w').close()
        return data_file

    def create_joblist(self, **kwargs):
        '''
        Create a joblist for parallel computing.

        Parameters
        ----------
        **kwargs: dict
            additional input arguments as key-value pairs:
            * "batch_size": number of image acquisition sites per job (*int*)

        Returns
        -------
        Dict[str, List[dict] or dict]
            job descriptions
        '''
        joblist = dict()
        joblist['run'] = list()
        layer_names = [
            layer['name']
            for layer in self.pipe['images']['layers']
        ]
        metadata = list()
        for cycle in self.cycles:
            metadata.extend([
                md for md in cycle.layer_metadata if md.name in layer_names
            ])
        md_batches = self._create_batches(metadata, kwargs['batch_size'])
        joblist['run'] = [{
                'id': i+1,
                'inputs': {
                    md.name: md.files for md in batch
                },
                'outputs': {
                    'data_file': self.create_data_file(i+1),
                    'figure_files': [
                        module.build_figure_filename(
                            self.figures_dir, i+1)
                        for module in self.pipeline
                    ],
                    'log_files': [
                        module.build_log_filenames(
                            self.module_log_dir, i+1).values()
                        for module in self.pipeline
                    ]
                }
            } for i, batch in enumerate(md_batches)]

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
                            pipe=self.pipe,
                            handles=self.handles)
        checker.check_all()
        self.start_engines()
        job_id = batch['id']
        self.create_data_file(job_id-1)
        outputs = collections.defaultdict(dict)
        outputs['data'] = dict()
        for module in self.pipeline:
            log_files = module.build_log_filenames(self.logs_dir, job_id)
            figure_file = module.build_figure_filename(self.figures_dir, job_id)
            data_file = self.build_data_filename(job_id)
            inputs = module.prepare_inputs(
                        job_description=batch, upstream_output=outputs['data'],
                        data_file=data_file, figure_file=figure_file)
            out = module.run(inputs, self.engines[module.language])
            module.write_output_and_errors(log_files['stdout'], out['stdout'],
                                           log_files['stderr'], out['stderr'])
            if not out['success']:
                sys.exit(out['error_message'])
            for k, v in out.iteritems():
                if k == 'data':
                    outputs['data'].update(out[k])
                else:
                    outputs[k][module.name] = out[k]

    def collect_job_output(self, batch, **kwargs):
        '''
        Collect and fuse *data* created by pipelines.

        Parameters
        ----------
        batch: dict
            description of the *collect* job
        **kwargs: dict
            additional variable input arguments as key-value pairs
        '''
        # TODO: dafu
        pass

    def apply_statistics(self, joblist, wells, sites, channels, output_dir,
                         **kwargs):
        raise AttributeError('"%s" object doesn\'t have a "apply_statistics"'
                             ' method' % self.__class__.__name__)
