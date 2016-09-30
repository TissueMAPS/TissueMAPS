import os
import re
import glob
import ruamel.yaml
import yaml
import logging
import shutil
from cached_property import cached_property
from natsort import natsorted

from tmlib.workflow.jterator.utils import get_module_directories
from tmlib.readers import YamlReader
from tmlib.writers import YamlWriter
from tmlib.errors import PipelineOSError
from tmlib.errors import PipelineDescriptionError

logger = logging.getLogger(__name__)

HANDLES_SUFFIX = '.handles.yaml'
PIPE_SUFFIX = '.pipe.yaml'


def list_projects(directory):
    '''Lists Jterator projects in a given directory.
    A Jterator project is defined as a folder containing a `.pipe` file.

    Parameters
    ----------
    directory: str
        absolute path to a directory
    '''
    return [
        os.path.join(directory, name)
        for name in os.listdir(directory)
        if os.path.isdir(os.path.join(directory, name)) and
        glob.glob(os.path.join(directory, name, '*%s' % PIPE_SUFFIX))
    ]


class Project(object):

    '''A Jterator project is defined as a folder containing a `.pipe` file.
    The class holds information about the project, in particular on the content
    of YAML pipeline and module descriptor files that can be edited in the
    JtUI app.
    '''
    def __init__(self, step_location, name, pipe=None, handles=None):
        '''
        Parameters
        ----------
        step_location: str
            path to the project folder
        name: str
            name of the pipeline
        pipe: dict, optional
            pipeline description (default: ``None``)
        handles: List[dict], optional
            module descriptions (default: ``None``)
        '''
        self.step_location = step_location
        # TODO: check validity of "name"
        self.name = name
        self.pipe = pipe
        self.handles = handles

    @property
    def pipe(self):
        '''dict: name and description of the pipeline'''
        if self._pipe is None:
            self._pipe = self._create_pipe()
        return self._pipe

    @pipe.setter
    def pipe(self, value):
        self._pipe = value

    @property
    def handles(self):
        '''List[dict]: name and description of modules'''
        if self._handles is None:
            self._handles = self._create_handles()
        return self._handles

    @handles.setter
    def handles(self, value):
        # Ensure that handles descriptions are sorted according to the order
        # specified in the pipeline description.
        if value is not None:
            handles_names = [v['name'] for v in value]
            handles = list()
            for module in self.pipe['description']['pipeline']:
                index = handles_names.index(module['name'])
                handles.append(value[index])
        else:
            handles = value
        self._handles = handles

    @property
    def _pipe_filename(self):
        '''str: name of the YAML pipeline descriptor file
        '''
        return '%s%s' % (self.name, PIPE_SUFFIX)

    def _get_pipe_file(self, directory=None):
        if not directory:
            directory = self.step_location
        pipe_files = glob.glob(
            os.path.join(directory, self._pipe_filename)
        )
        if len(pipe_files) == 1:
            return pipe_files[0]
        elif len(pipe_files) > 1:
            raise PipelineOSError(
                'More than more pipeline descriptor file found: %s' % directory
            )
        else:
            raise PipelineOSError(
                'No pipeline descriptor file found: %s' % directory
            )

    def _get_handles_files(self, directory=None):
        if not directory:
            directory = os.path.join(self.step_location, 'handles')
        else:
            directory = os.path.join(directory, 'handles')
        if not os.path.exists(directory):
            logger.debug('create handles directory')
            os.mkdir(directory)
        handles_files = glob.glob(
            os.path.join(directory, '*%s' % HANDLES_SUFFIX)
        )
        if not handles_files:
            # We don't raise an exception, because an empty handles folder
            # can occur, for example upon creation of a new project
            logger.warning('No handles files found: %s' % directory)
        return handles_files

    @staticmethod
    def _get_descriptor_name(filename):
        return os.path.splitext(
            os.path.splitext(os.path.basename(filename))[0]
        )[0]

    @staticmethod
    def _replace_values(old, new):
        # Recursively replace values in the `old` mapping with those of `new`.
        # NOTE: This is not a general approach, but targeted for the design of
        # the pipeline and module descriptor files.
        # TODO: make this general using a recursive strategy
        for k1, v1 in old.iteritems():
            # 'project', 'images', and 'description' keys in the pipeline
            # descriptor file or 'input' and 'output' keys in the module
            # descriptor file
            if isinstance(v1, dict):
                # this affects 'project' and 'jobs'
                for k2, v2 in v1.iteritems():
                    if isinstance(v2, list):
                        # this is the array of 'layers' in the 'images' section
                        old[k1][k2] = []
                        for i, element in enumerate(new[k1][k2]):
                            if isinstance(element, dict):
                                old[k1][k2].append(new[k1][k2][i])

                    else:
                        old[k1][k2] = new[k1][k2]
            elif isinstance(v1, list):
                # this affects the 'description' key in the pipeline descriptor
                # file and the 'input' and 'output' keys in the module
                # descriptor file
                old[k1] = []
                for i, element in enumerate(new[k1]):
                    if isinstance(element, dict):
                        old[k1].append(new[k1][i])
            else:
                old[k1] = new[k1]
        return old

    def _create_pipe(self):
        with YamlReader(self.pipe_file) as f:
            pipe = {
                'name': self._get_descriptor_name(self.pipe_file),
                'description': f.read()
            }
        # We need to do some basic checks here, because this code gets executed
        # before the actual checks in checker.py.
        if 'pipeline' not in pipe['description']:
            raise PipelineDescriptionError(
                'Pipeline descriptor file "%s" must contain key "pipeline".'
                % self.pipe_file
            )
        if pipe['description']['pipeline']:
            if not isinstance(pipe['description']['pipeline'], list):
                raise PipelineDescriptionError(
                    'Pipeline description in "%s" must be an array.'
                    % self.pipe_file
                )
            # Add module 'name' to pipeline for display in the interface
            for i, module in enumerate(pipe['description']['pipeline']):
                if 'handles' not in pipe['description']['pipeline'][i]:
                    raise PipelineDescriptionError(
                        'Element #%d of "pipeline" array in pipeline '
                        'descriptor file "%s" must contain key "handles".'
                        % (i, self.pipe_file)
                    )
                pipe['description']['pipeline'][i]['name'] = \
                    self._get_descriptor_name(
                        pipe['description']['pipeline'][i]['handles']
                    )
        else:
            logger.warn(
                'no pipeline description provided in "%s"', self.pipe_file
            )
        return pipe

    @property
    def _module_names(self):
        return [m['name'] for m in self.pipe['description']['pipeline']]

    def _create_handles(self):
        handles = list()
        handles_files = self._get_handles_files()
        if handles_files:
            for h_file in handles_files:
                if not os.path.isabs(h_file):
                    h_file = os.path.join(self.step_location, h_file)
                if not os.path.exists(h_file):
                    raise PipelineOSError(
                        'Handles file does not exist: "%s"' % h_file
                    )
                with YamlReader(h_file) as f:
                    handles.append({
                        'name': self._get_descriptor_name(h_file),
                        'description': f.read()
                    })
        # Sort handles information according to order of modules in the pipeline
        names = [h['name'] for h in handles]
        sorted_handles = list()
        for name in self._module_names:
            if name not in names:
                raise ValueError(
                    'Handles for module "%s" does not exist.' % name
                )
            sorted_handles.append(handles[names.index(name)])

        return sorted_handles

    @cached_property
    def pipe_file(self):
        '''str: absolute path to the pipeline descriptor file

        Note
        ----
        Creates the file with an empty pipeline description in case it doesn't
        exist.
        '''
        pipe_file= os.path.join(
            self.step_location, self._pipe_filename
        )
        if not os.path.exists(pipe_file):
            self._create_pipe_file(pipe_file)
        return pipe_file

    def _create_pipe_file(self, filename):
        logger.info('create pipeline descriptor file: %s', filename)
        pipe = {
            'description': str(),
            'input': {
                'channels': [
                    {'name': str(), 'correct': True}
                ]
            },
            'pipeline': list()
        }
        with YamlWriter(filename) as f:
            f.write(pipe)
        return pipe

    def _create_handles_folder(self):
        handles_dir = os.path.join(self.step_location, 'handles')
        logger.info('create handles directory: %s', handles_dir)
        if not os.path.exists(handles_dir):
            os.mkdir(handles_dir)

    def _create_project_from_skeleton(self, skel_dir, repo_dir=None):
        pipe_file = self._get_pipe_file(skel_dir)
        if not repo_dir:
            shutil.copy(pipe_file, self.step_location)
        else:
            with YamlReader(pipe_file) as f:
                pipe_content = f.read()
            new_pipe_file = os.path.join(
                self.step_location, '%s%s' % (self.name, PIPE_SUFFIX)
            )
            with YamlWriter(new_pipe_file) as f:
                f.write(pipe_content)
        shutil.copytree(
            os.path.join(skel_dir, 'handles'),
            os.path.join(self.step_location, 'handles')
        )

    def _remove_pipe_file(self, name):
        pipe_file = os.path.join(
            self.step_location, '%s%s' % (name, PIPE_SUFFIX)
        )
        os.remove(pipe_file)

    def _remove_handles_folder(self):
        handles_dir = os.path.join(self.step_location, 'handles')
        shutil.rmtree(handles_dir)

    def _modify_pipe(self):
        pipe_file = self._get_pipe_file()
        with YamlReader(pipe_file) as f:
            old_pipe_content = f.read()
        new_pipe_content = self.pipe['description']
        # Remove module 'name' from pipeline (only used internally)
        for i, module in enumerate(new_pipe_content['pipeline']):
            new_pipe_content['pipeline'][i].pop('name', None)
        mod_pipe_content = self._replace_values(
            old_pipe_content, new_pipe_content
        )
        with YamlWriter(pipe_file) as writer:
            writer.write(mod_pipe_content)

    def _modify_handles(self):
        handles_files = []
        # Create new .handles files for added modules
        for h in self.handles:
            filename = os.path.join(
                self.step_location, 'handles',
                '%s%s' % (h['name'], HANDLES_SUFFIX)
            )
            handles_files.append(filename)
            for i, handles_file in enumerate(handles_files):
                # If file already exists, modify its content
                if os.path.exists(handles_file):
                    with YamlReader(handles_file) as f:
                        old_handles_content = f.read()
                    new_handles_content = self.handles[i]['description']
                    mod_handles_content = self._replace_values(
                        old_handles_content, new_handles_content
                    )
                # If file doesn't yet exist, create it and add content
                else:
                    mod_handles_content = self.handles[i]['description']
                with YamlWriter(handles_file) as f:
                    f.write(mod_handles_content)
        # Remove .handles file that are no longer in the pipeline
        existing_handles_files = glob.glob(
            os.path.join(self.step_location, 'handles', '*%s' % HANDLES_SUFFIX)
        )
        for f in existing_handles_files:
            if f not in handles_files:
                os.remove(f)

    def as_dict(self):
        '''Returns the attributes as key-value pairs.

        Returns
        -------
        dict
        '''
        attrs = dict()
        attrs['name'] = self.name
        attrs['pipe'] = yaml.safe_load(
            ruamel.yaml.dump(self.pipe, Dumper=ruamel.yaml.RoundTripDumper)
        )
        attrs['handles'] = [
            yaml.safe_load(
                ruamel.yaml.dump(h, Dumper=ruamel.yaml.RoundTripDumper)
            )
            for h in self.handles
        ]
        return attrs

    def save(self):
        '''Saves a Jterator project:
        Updates the content of *.pipe* and *.handles* files on disk
        according to modifications to the pipeline and module descriptions.
        '''
        if not os.path.exists(self.step_location):
            raise PipelineOSError(
                'Project does not exist: %s' % self.step_location
            )
        self._modify_pipe()
        self._modify_handles()

    def create(self, repo_dir=None, skel_dir=None):
        '''Creates a Jterator project:
        Create the project folder and an empty "handles" subfolder as well as
        a skeleton *.pipe* file, i.e. a pipeline descriptor file with all
        required main keys but an empty module list.
        When `skel_dir` is provided, the *.pipe* and *.handles* files are
        copied.

        Parameters
        ----------
        repo_dir: str, optional
            path to repository directory where module files are located
        skel_dir: str, optional
            path to repository directory that represents a project skeleton,
            i.e. contains a *.pipe* and one or more *.handles* files in a
            *handles* directory.
        '''
        if repo_dir:
            repo_dir = os.path.expandvars(repo_dir)
            repo_dir = os.path.expanduser(repo_dir)
            repo_dir = os.path.abspath(repo_dir)
        if skel_dir:
            skel_dir = os.path.expandvars(skel_dir)
            skel_dir = os.path.expanduser(skel_dir)
            skel_dir = os.path.abspath(skel_dir)
        # if os.path.exists(self.step_location):
        #     raise PipelineOSError(
        #         'Project already exists. Remove existing project first.'
        #     )
        # os.mkdir(self.step_location)
        # TODO: handle creation of project based on provided pipe
        if skel_dir:
            self._create_project_from_skeleton(skel_dir, repo_dir)
        else:
            pipe_file_path = os.path.join(
                self.step_location, self._pipe_filename
            )
            self._create_pipe_file(pipe_file_path)
            self._create_handles_folder()

    def remove(self):
        '''
        Remove a Jterator project, i.e. kill the folder on disk.
        '''
        # remove_pipe_file(self.step_location, self.pipe['name'])
        # remove_handles_folder(self.step_location)
        if not os.path.exists(self.step_location):
            raise PipelineOSError(
                'Project does not exist: %s' % self.step_location
            )
        shutil.rmtree(self.step_location)


class AvailableModules(object):

    '''Container for information about Jterator modules available
    in the `JtLibrary <https://github.com/TissueMAPS/JtLibrary>`_ repository.
    '''

    def __init__(self, repo_dir):
        '''
        Initialize an instance of class AvailableModules.

        Parameters
        ----------
        repo_dir: str
            absolute path to the local clone of the repository
        '''
        self.repo_dir = repo_dir

    @property
    def module_files(self):
        '''
        Module files are assumed to reside in a package called "modules"
        as a subpackage of the "jtlib" package. Module files can have one of
        the following extensions: ".py", ".m", ".jl", ".r" or ".R".

        Returns
        -------
        List[str]
            absolute paths to module files
        '''
        dirs = get_module_directories(self.repo_dir)
        search_strings = {
            'Python': '^[^_]+.*\.py$',  # exclude _ files
            'Matlab': '\.m$',
            'R': '\.(%s)$' % '|'.join(['r', 'R']),
        }
        modules = list()
        for languange, d in dirs.iteritems():
            r = re.compile(search_strings[languange])
            modules.extend([
                os.path.join(d, f)
                for f in os.listdir(d) if r.search(f)
            ])
        return natsorted(modules)

    @property
    def module_names(self):
        '''List[str]: names of the modules (determined from file names)
        '''
        return [
            os.path.splitext(os.path.basename(f))[0]
            for f in self.module_files
        ]

    @property
    def module_languages(self):
        '''List[str]: languages of the modules (determined from file suffixes)
        '''
        mapping = {
            '.py': 'python',
            '.m': 'matlab',
            '.jl': 'julia',
            '.r': 'r',
            '.R': 'r'
        }
        suffixes = [
            os.path.splitext(os.path.basename(f))[1]
            for f in self.module_files
        ]
        languages = list()
        for s in suffixes:
            if s not in mapping.keys():
                raise ValueError('Not a valid file extension: %s', s)
            languages.append(mapping[s])
        return languages

    def _get_handles_file(self, module_name):
        handles_dir = os.path.join(self.repo_dir, 'handles')
        search_string = '^%s\%s$' % (module_name, HANDLES_SUFFIX)
        regexp_pattern = re.compile(search_string)
        handles_files = natsorted([
            os.path.join(handles_dir, f)
            for f in os.listdir(handles_dir)
            if re.search(regexp_pattern, f)
        ])
        if len(handles_files) == 0:
            raise ValueError(
                'No handles file found for module "%s"' % module_name
            )
        elif len(handles_files) == 1:
            # NOTE: we assume that handles are stored within a subfolder of the
            # project folder, which is called "handles"
            return handles_files[0]

    @property
    def handles(self):
        '''
        Handles files are assumed to reside in a subfolder called "handles"
        and have the suffix ".handles.yml".

        Returns
        -------
        List[dict]
            name and description for each handles file
        '''
        handles = list()
        for name in self.module_names:
            with YamlReader(self._get_handles_file(name)) as f:
                handles.append({'name': name, 'description': f.read()})
        return handles

    @property
    def pipe_registration(self):
        '''Build pipeline elements for registration in the UI
        in the format excepted in the "pipeline" section in the `.pipe` file.

        Returns
        -------
        List[dict]
            pipeline elements
        '''
        # modules are "available" if there is a corresponding handles file
        # TODO: some checks of handles content
        available_modules = [h['name'] for h in self.handles]
        self._pipe_registration = list()
        for i, name in enumerate(self.module_names):
            name = self.module_names[i]
            filename = os.path.basename(self.module_files[i])
            if name in available_modules:
                try:
                    repo_handles_path = self._get_handles_file(name)
                except:
                    logger.error('no handles file found for module "%s"', name)
                    continue
                # We have to provide the path to handles files for the
                # currently processed project
                new_handles_path = os.path.join(
                    'handles', os.path.basename(repo_handles_path))
                element = {
                    'name': name,
                    'description': {
                        'handles': new_handles_path,
                        'source': filename,
                        'active': True
                    }
                }
                self._pipe_registration.append(element)
        return self._pipe_registration

    def as_dict(self):
        '''Returns attributes as key-value pairs

        Returns
        -------
        dict
        '''
        attrs = dict()
        attrs['modules'] = self.handles
        attrs['registration'] = self.pipe_registration
        return attrs
