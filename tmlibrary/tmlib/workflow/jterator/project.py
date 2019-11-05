# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016-2019 University of Zurich.
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
try:
    from collections.abc import Iterable  # Python 3
except ImportError:
    from collections import Iterable  # Python 2.7
import os
import re
import glob
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

# see: https://stackoverflow.com/a/27519509/459543
yaml.SafeLoader.add_constructor(
    "tag:yaml.org,2002:python/unicode",
    lambda loader, node: node.value)

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
            try:
                with YamlReader(h_file) as f:
                    content = f.read()
                description = HandleDescriptions(**content)
                h = Handles(name, description)
                handles.append(h)
            except Exception as err:
                logger.error(
                    "Cannot instanciate module `%s`: %s: %s",
                    name, err.__class__.__name__, err)
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

    def _copy_project_from_skeleton(self, skel_dir):
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
        attrs['pipe'] = self.pipe.to_dict()
        attrs['handles'] = [ h.to_dict() for h in self.handles ]
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
            ``handles/`` directory.
        '''
        if skel_dir:
            skel_dir = os.path.abspath(
                os.path.expandvars(
                    os.path.expanduser(skel_dir)))
            self._copy_project_from_skeleton(skel_dir)
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


# FIXME: there's no local state saved in instances of this class. This
# means we are using the `class` definition as a mere
# container/namespace for functions. Consider making it a module.
class AvailableModules(object):
    '''
    Container for information about available Jterator modules.
    A module is "available" if it has an accompanying "handles"
    YAML file.

    See also
    --------
    :attr:`tmlib.config.LibraryConfig.modules_path`
    '''

    _MODULE_LANGUAGE_EXT = {
        '.py': 'python',
        '.m': 'matlab',
        '.jl': 'julia',
        '.r': 'r',
        '.R': 'r',
    }
    '''
    Map file suffix to corresponding programming language.
    '''

    def _strip_well_known_suffix(self, pathname):
        stem, suffix = os.path.splitext(pathname)
        if suffix in self._MODULE_LANGUAGE_EXT:
            return stem
        else:
            return pathname

    def find_module_by_name(self, name):
        '''
        Return absolute path to module with the given name.

        If multiple modules match, only the first one is returned.
        '''
        name = self._strip_well_known_suffix(name)
        module_files = self.module_files  # compute once
        if not module_files:
            logger.error("Module file list is empty!")
        else:
            for module_file in module_files:
                if name == self._get_module_name_from_file(module_file):
                    logger.debug("Using source file `%s` for module `%s`", module_file, name)
                    return module_file
            logger.error(
                "Could not find module `%s` among module files %r",
                name, module_files)
        raise LookupError("Cannot find module `{0}`".format(name))


    # FIXME: this gets called over and over again by `.modules_names`
    # etc. -- every time we walk the filesystem to list available
    # modules.  We should instead cache results per-directory, and
    # only rebuild (a part of) the cache when a directory is changed
    # (directory mtime > cache build epoch).
    @property
    def module_files(self):
        '''
        List[str]: absolute paths to module files

        Note
        ----
        Module files are assumed to reside in any of the directories
        listed in configuration value `modules_path`.  They can have
        one of the following extensions: ".py", ".m", ".r" or ".R",
        and must start with an ASCII letter.
        '''
        all_modules = []
        for path in cfg.modules_path:
            if not os.path.exists(path):
                logger.warn(
                    'modules directory `%s` does not exist;'
                    ' ignoring it!', path)
                continue
            all_modules += [
                os.path.join(path, f)
                for f in os.listdir(path)
                if self._MODULE_FILENAME_RE.search(f)
            ]
        return natsorted(all_modules)

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
            self._get_module_name_from_file(f)
            for f in self.module_files
        ]

    def _get_module_name_from_file(self, module_file):
        '''
        Return the module name given the (absolute) filesystem path.
        '''
        return self._strip_well_known_suffix(os.path.basename(module_file))

    @property
    def module_languages(self):
        '''List[str]: languages of the modules (determined from file suffixes)
        '''
        # FIXME: why is this a list? shouldn't it be a set?
        suffixes = [
            os.path.splitext(os.path.basename(f))[1]
            for f in self.module_files
        ]
        try:
            return [self._MODULE_LANGUAGE_EXT[item] for item in suffixes]
        except KeyError:
            # FIXME: this gives no hint what file/module the errors comes from!
            # FIXME: should "ignore errors" be the default policy instead,
            # and only raise an `AssertionError` when debugging/developing?
            raise ValueError(
                'Not a valid file extension: {0}'
                .format(s))


    # FIXME: this also triggers reading back *all* `handles.yml` files;
    # we should cache the results and only reload when handles have changed.
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
        for module_file in self.module_files:
            name = self._get_module_name_from_file(module_file)
            try:
                with YamlReader(self._get_handles_file(module_file)) as y:
                    handles.append({
                        # FIXME: why not a NamedTuple??
                        'name': name,
                        'description': y.read(),
                    })
            except Exception as err:
                logging.warning("Cannot read handles file for module `%s`: %s", name, err)
                continue
        return handles

    def _get_handles_file(self, module_file):
        '''
        Return handles file for the given module.

        The "handles" file path is gotten from the (absolute) path
        name of the module file by changing the extension with
        ``.handles.yaml`` (see: `HANDLES_SUFFIX` in this Python module).
        '''
        assert os.path.isabs(module_file), (
            "argument `module_file` to `AvailableModules._get_handles_file`"
            " must be an absolute path")
        stem, suffix = os.path.splitext(module_file)
        handles_file = (stem + HANDLES_SUFFIX)
        if not os.path.exists(handles_file):
            raise LookupError(
                "Handles file `{0}` does not exist!"
                .format(handles_file))
        return handles_file


    def to_dict(self):
        '''Returns attributes as key-value pairs

        Returns
        -------
        dict
        '''
        handles = self.handles  # only compute once
        return {
            'modules': handles,
            'registration': self._make_pipe_registration(handles),
        }

    # FIXME: what the heck is a "pipe registration"?!
    def _make_pipe_registration(self, handles):
        '''Build pipeline elements for registration in the UI
        in the format excepted in the "pipeline" section in the *pipeline* file.

        Parameters
        ----------
        handles
          Return value of `self.handles`:meth: (which see),
          passed as argument to avoid recomputing.

        Returns
        -------
        List[dict]
            pipeline elements
        '''
        # modules are "available" if there is a corresponding handles file
        available_modules = [h['name'] for h in handles]
        result = []
        for filename in self.module_files:
            name = self._get_module_name_from_file(filename)
            if name in available_modules:
                try:
                    # FIXME: check that contents of the "handles" file are valid
                    handles_file = self._get_handles_file(filename)
                except LookupError as err:
                    logger.warning('No handles file found for module `%s`', name)
                    continue
                # We have to provide the path to handles files for the
                # currently processed project
                # FIXME: cross-check that "project" creation copies the "handles"
                # files into a project-specific "handles" directory, and why is that needed?
                new_handles_file = os.path.join('handles', os.path.basename(handles_file))
                element = {
                    'name': name,
                    'description': {
                        'handles': new_handles_file,
                        'source': filename,
                        'active': True
                    }
                }
                result.append(element)
        return result
