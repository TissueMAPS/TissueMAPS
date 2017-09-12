# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import os
import re
import glob
import ruamel.yaml
import yaml
import logging
import shutil
from cached_property import cached_property
from natsort import natsorted

from tmlib import cfg
from tmlib.workflow.jterator.description import (
    PipelineDescription, HandleDescriptions
)
from tmlib.readers import YamlReader
from tmlib.writers import YamlWriter
from tmlib.errors import PipelineOSError
from tmlib.errors import PipelineDescriptionError

logger = logging.getLogger(__name__)

HANDLES_SUFFIX = '.handles.yaml'


class Pipe(object):

    '''Representation of the content of the *pipeline.yaml* file.'''

    __slots__ = ('_description', )

    def __init__(self, description):
        '''
        Parameters
        ----------
        description: tmlib.workflow.jterator.description.PipelineDescription
            pipeline description
        '''
        self.description = description

    @property
    def description(self):
        '''tmlib.workflow.jterator.description.PipelineDescription:
        pipeline description
        '''
        return self._description

    @description.setter
    def description(self, value):
        if not isinstance(value, PipelineDescription):
            raise TypeError(
                'Attibute "description" must have type PipelineDescription.')
        self._description = value

    def to_dict(self):
        '''Returns attribute "description" as key-value pairs.

        Returns
        -------
        dict
        '''
        # NOTE: We need to include the name of modules in the pipelines for
        # compatibility with the viewer.
        return {
            'description': {
                'input': self.description.input.to_dict(),
                'output': self.description.output.to_dict(),
                'pipeline': [
                    {
                        'name': m.name, 'source': m.source,
                        'handles': m.handles, 'active': m.active
                    }
                    for m in self.description.pipeline
                ]
            }
        }


class Handles(object):

    '''Representation of the content of a *.handles.yaml* file.'''

    __slots__ = ('_description', '_name')

    def __init__(self, name, description):
        '''
        Parameters
        ----------
        name: str
            module name
        description: tmlib.workflow.jterator.description.HandleDescriptions
            module description
        '''
        self.name = name
        self.description = description

    @property
    def name(self):
        '''str: module name'''
        return self._name

    @name.setter
    def name(self, value):
        if not isinstance(value, basestring):
            raise TypeError('Attribute "name" must have type basestring.')
        self._name = str(value)

    @property
    def description(self):
        '''tmlib.workflow.jterator.description.HandleDescriptions:
        module description
        '''
        return self._description

    @description.setter
    def description(self, value):
        if not isinstance(value, HandleDescriptions):
            raise TypeError(
                'Attibute "description" must have type HandleDescriptions.')
        self._description = value

    def to_dict(self):
        '''Returns attributes "name" and "description" as key-value pairs.

        Returns
        -------
        dict
        '''
        return {
            'name': self.name,
            'description': self.description.to_dict()
        }


class Project(object):

    '''A project is defined as a folder containing a *pipeline.yaml*
    file and a *handles* subfolder with zero or more *.handles.yaml* files.
    The class holds information about the project, in particular on the content
    of the *pipeline.yaml* and *.handles.yaml* module descriptor files and
    provides methods for retrieving, updating and removing the project.
    '''

    def __init__(self, location, pipeline_description=None,
            handles_descriptions=None):
        '''
        Parameters
        ----------
        location: str
            path to the project folder
        pipeline_description: tmlib.workflow.jterator.description.PipelineDescription, optional
            pipeline description (default: ``None``)
        handles_descriptions: Dict[str, tmlib.workflow.jterator.description.HandleDescriptions], optional
            module descriptions (default: ``None``)
        '''
        self.location = location
        if not os.path.exists(self._get_pipe_file()):
            self.create()
        if pipeline_description is None:
            self.pipe = self._create_pipe()
        else:
            self.pipe = Pipe(pipeline_description)
        if handles_descriptions is None:
            self.handles = self._create_handles()
        else:
            handles = list()
            for m in self.pipe.description.pipeline:
                h = Handles(m.name, handles_descriptions[m.name])
                handles.append(h)
            self.handles = handles

    @property
    def pipe(self):
        '''tmlib.workflow.jterator.project.Pipe: pipeline description
        '''
        return self._pipe

    @pipe.setter
    def pipe(self, value):
        if not isinstance(value, Pipe):
            raise TypeError('Attribute "pipe"')
        self._pipe = value

    @property
    def handles(self):
        '''List[tmlib.workflow.jterator.project.Handles]: module descriptions
        '''
        return self._handles

    @handles.setter
    def handles(self, value):
        if not isinstance(value, list):
            raise TypeError('Attribute "handles" must have type list.')
        for v in value:
            if not isinstance(v, Handles):
                raise TypeError(
                    'Items of attribute "handles" must have type Handles.'
                )
        self._handles = value

    @property
    def _pipe_filename(self):
        return 'pipeline.yaml'

    def _get_pipe_file(self, directory=None):
        if not directory:
            directory = self.location
        pipe_files = glob.glob(
            os.path.join(directory, self._pipe_filename)
        )
        if len(pipe_files) == 1:
            return pipe_files[0]
        elif len(pipe_files) > 1:
            raise PipelineOSError(
                'More than one pipeline descriptor file found: %s' % directory
            )
        else:
            return self.pipe_file

    def _get_handles_file(self, name, directory=None):
        if not directory:
            directory = os.path.join(self.location, 'handles')
        else:
            directory = os.path.join(directory, 'handles')
        if not os.path.exists(directory):
            logger.debug('create handles directory')
            os.mkdir(directory)
        return os.path.join(directory, '%s%s' % (name, HANDLES_SUFFIX))

    def _create_pipe(self):
        with YamlReader(self.pipe_file) as f:
            content = f.read()
        try:
            description = PipelineDescription(**content)
        except TypeError as err:
            raise PipelineDescription(
                'Incorrect pipeline description: %s' % str(err)
            )
        return Pipe(description)

    @property
    def _module_names(self):
        return [m.name for m in self.pipe.description.pipeline]

    def _create_handles(self):
        handles = list()
        for name in self._module_names:
            h_file = self._get_handles_file(name)
            with YamlReader(h_file) as f:
                content = f.read()
            try:
                description = HandleDescriptions(**content)
            except TypeError as err:
                raise PipelineDescription(
                    'Incorrect handles description of module "%s": %s' % (
                        name, str(err)
                    )
                )
            h = Handles(name, description)
            handles.append(h)
        return handles

    @cached_property
    def pipe_file(self):
        '''str: absolute path to the pipeline descriptor file

        Note
        ----
        Creates the file with an empty pipeline description in case it doesn't
        exist.
        '''
        pipe_file= os.path.join(
            self.location, self._pipe_filename
        )
        if not os.path.exists(pipe_file):
            self._create_pipe_file(pipe_file)
        return pipe_file

    def _create_pipe_file(self, filename):
        logger.info('create pipeline descriptor file: %s', filename)
        pipe = {
            'input': {
                'channels': list(),
                'objects': list()
            },
            'pipeline': list(),
            'output': {
                'objects': list()
            }
        }
        with YamlWriter(filename) as f:
            f.write(pipe)
        return pipe

    def _create_handles_folder(self):
        handles_dir = os.path.join(self.location, 'handles')
        logger.info('create handles directory: %s', handles_dir)
        if not os.path.exists(handles_dir):
            os.mkdir(handles_dir)

    def _create_project_from_skeleton(self, skel_dir):
        skel_pipe_file = self._get_pipe_file(skel_dir)
        shutil.copy(skel_pipe_file, self.location)
        shutil.copytree(
            os.path.join(skel_dir, 'handles'),
            os.path.join(self.location, 'handles')
        )

    def _remove_pipe_file(self, name):
        pipe_file = os.path.join(self.location, self._pipe_filename)
        os.remove(pipe_file)

    def _remove_handles_folder(self):
        handles_dir = os.path.join(self.location, 'handles')
        shutil.rmtree(handles_dir)

    def _update_pipe(self):
        pipe_file = self._get_pipe_file()
        with YamlWriter(pipe_file) as f:
            f.write(self.pipe.description.to_dict())

    def _update_handles(self):
        handles_files = []
        # Create new .handles files for added modules
        old_handles_files = glob.glob(
            os.path.join(self.location, 'handles', '*%s' % HANDLES_SUFFIX)
        )
        new_handles_files = list()
        for h in self.handles:
            filename = self._get_handles_file(h.name)
            new_handles_files.append(filename)
            with YamlWriter(filename) as f:
                f.write(h.description.to_dict())
        # Remove .handles file that are no longer in the pipeline
        for f in old_handles_files:
            if f not in new_handles_files:
                os.remove(f)

    def to_dict(self):
        '''Returns attributes "pipe" and "handles" as key-value pairs.

        Returns
        -------
        dict
        '''
        attrs = dict()
        attrs['pipe'] = yaml.safe_load(
            ruamel.yaml.dump(
                self.pipe.to_dict(), Dumper=ruamel.yaml.RoundTripDumper
            )
        )
        attrs['handles'] = [
            yaml.safe_load(
                ruamel.yaml.dump(
                    h.to_dict(), Dumper=ruamel.yaml.RoundTripDumper
                )
            )
            for h in self.handles
        ]
        return attrs

    def save(self):
        '''Saves a Jterator project:
        Updates the content of *pipeline* and *handles* files on disk
        according to modifications to the pipeline and module descriptions.
        '''
        if not os.path.exists(self.location):
            raise PipelineOSError(
                'Project does not exist: %s' % self.location
            )
        self._update_pipe()
        self._update_handles()

    def create(self, skel_dir=None):
        '''Creates a Jterator project:
        Creates an empty "handles" subfolder as well as a skeleton pipeline
        file, i.e. a pipeline descriptor file with all required main keys but
        an empty module list. When `skel_dir` is provided, *pipeline* and
        *handles* files are copied.

        Parameters
        ----------
        skel_dir: str, optional
            path to repository directory that represents a project skeleton,
            i.e. contains a *pipeline* and one or more *handles* files in a
            *handles* directory.
        '''
        if skel_dir:
            skel_dir = os.path.expandvars(skel_dir)
            skel_dir = os.path.expanduser(skel_dir)
            skel_dir = os.path.abspath(skel_dir)
        # if os.path.exists(self.location):
        #     raise PipelineOSError(
        #         'Project already exists. Remove existing project first.'
        #     )
        # os.mkdir(self.location)
        # TODO: handle creation of project based on provided pipe
        if skel_dir:
            self._create_project_from_skeleton(skel_dir, cfg.modules_home)
        else:
            pipe_file_path = os.path.join(
                self.location, self._pipe_filename
            )
            self._create_pipe_file(pipe_file_path)
            self._create_handles_folder()

    def remove(self):
        '''Removes a Jterator project.'''
        # remove_pipe_file(self.location, self.pipe['name'])
        # remove_handles_folder(self.location)
        if not os.path.exists(self.location):
            raise PipelineOSError(
                'Project does not exist: %s' % self.location
            )
        shutil.rmtree(self.location)


class AvailableModules(object):

    '''Container for information about Jterator modules available
    in a local copy of the
    `JtModules <https://github.com/TissueMAPS/JtModules>`_ repository.

    See also
    --------
    :attr:`tmlib.config.LibraryConfig.modules_home`
    '''

    def __init__(self):
        if not os.path.exists(cfg.modules_home):
            raise OSError(
                'Local JtModules repository does not exist: %s'
                % cfg.modules_home
            )

    @property
    def module_files(self):
        '''List[str]: absolute paths to module files

        Note
        ----
        Module files are assumed to reside in a package called "modules"
        as a subpackage of the "jtlib" package. They can have one of
        the following extensions: ".py", ".m", ".r" or ".R", and must
        start with an ASCII letter.
        '''
        if not os.path.exists(cfg.modules_home):
            logger.warn(
                'modules directory does not exist: %s',
                cfg.modules_home
            )
            # no point in continuing
            return []
        modules = [
            os.path.join(cfg.modules_home, f)
            for f in os.listdir(cfg.modules_home)
            if self._MODULE_FILENAME_RE.search(f)
        ]
        return natsorted(modules)

    _MODULE_FILENAME_RE = re.compile(
        '^[a-zA-Z].*' # modules names must start with an ASCII letter
        '('
        r'\.py$'   # Python
        '|'
        r'\.m$'    # MATLAB
        '|'
        r'\.[rR]$' # R
        ')'
    )

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
        handles_dir = os.path.join(cfg.modules_home, '..', 'handles')
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
            try:
                with YamlReader(self._get_handles_file(name)) as f:
                    handles.append({'name': name, 'description': f.read()})
            except:
                continue
        return handles

    @property
    def pipe_registration(self):
        '''Build pipeline elements for registration in the UI
        in the format excepted in the "pipeline" section in the *pipeline* file.

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

    def to_dict(self):
        '''Returns attributes as key-value pairs

        Returns
        -------
        dict
        '''
        attrs = dict()
        attrs['modules'] = self.handles
        attrs['registration'] = self.pipe_registration
        return attrs
