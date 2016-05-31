import yaml
import re
import os
import logging
from os.path import splitext, basename, exists, dirname
from collections import Counter

from tmlib.workflow.jterator.utils import complete_path
from tmlib.workflow.jterator.utils import get_module_path
from tmlib.workflow.jterator.handles import create_handle
from tmlib.workflow.jterator.handles import PipeHandle
from tmlib.workflow.jterator.project import HANDLES_SUFFIX
from tmlib.readers import YamlReader
from tmlib.errors import PipelineDescriptionError

logger = logging.getLogger(__name__)


class PipelineChecker(object):

    '''Class for checking pipeline and handles descriptions.'''

    def __init__(self, step_location, pipe_description,
                 handles_descriptions=None):
        '''
        Parameters
        ----------
        step_location: str
            path to Jterator project folder
        pipe_description: dict
            pipeline description (module order)
        handles_descriptions: dict, optional
            list of module descriptions (module input/output)
        '''
        self.pipe_description = pipe_description
        self.handles_descriptions = handles_descriptions
        self.step_location = step_location

    def check_pipeline(self):
        '''Check pipeline structure.'''
        # Check "project" section
        if 'description' not in self.pipe_description.keys():
            raise PipelineDescriptionError(
                'Pipeline file must contain the key "description".'
            )
        if 'lib' in self.pipe_description.keys():
            libpath = self.pipe_description['lib']
            libpath = complete_path(libpath, self.step_location)
            if libpath:
                if not exists(libpath):
                    raise PipelineDescriptionError(
                        'The path defined by "lib" in your '
                        'pipeline file is not valid.'
                    )
        # Check "jobs" section
        if 'input' not in self.pipe_description.keys():
            raise PipelineDescriptionError(
                'Pipe file must contain the key "input".'
            )
        possible_keys = {'channels', 'mapobject_types'}
        for key in self.pipe_description['input']:
            if key not in possible_keys:
                raise PipelineDescriptionError(
                    'Possible subkeys of "inputs" are: "%s"'
                    % ", ".join(possible_keys)
                )

            if not isinstance(self.pipe_description['input'][key], list):
                raise PipelineDescriptionError(
                    'The value of "%s" in the "inputs" section '
                    'of the pipe file must be an array.' % key
                )
            # Check for presence of required keys
            REQUIRED_HANDLE_ITEM_KEYS = set()
            possible_subkeys = REQUIRED_HANDLE_ITEM_KEYS.union(
                {'correct', 'align', 'name'}
            )
            inputs = self.pipe_description['input'][key]
            for inpt in inputs:
                for k in REQUIRED_HANDLE_ITEM_KEYS:
                    if k not in inpt:
                        raise PipelineDescriptionError(
                            'Each element of "%s" in the "inputs" '
                            'section of the pipe file requires '
                            'key "%s".' % (key, k)
                        )
                for k in inpt:
                    if k not in possible_subkeys:
                        raise PipelineDescriptionError(
                            'Unknown key "%s" for "%s" '
                            'in "inputs" section of the pipe file.' % (k, key)
                        )

        # Check "pipeline" section
        if 'pipeline' not in self.pipe_description.keys():
            raise PipelineDescriptionError(
                    'Pipeline file must contain the key "pipeline".')
        if not isinstance(self.pipe_description['pipeline'], list):
            raise PipelineDescriptionError(
                    'The value of "pipeline" in the pipe file must be a list.')

        required_subkeys = {'handles', 'source', 'active'}
        for module_description in self.pipe_description['pipeline']:
            for key in required_subkeys:
                if key not in module_description:
                    raise PipelineDescriptionError(
                            'Each element in "pipeline" '
                            'in the pipe file needs a key "%s".' % key)
                if key == 'active':
                    if not isinstance(module_description[key], bool):
                        raise PipelineDescriptionError(
                                'The value of "%s" in the '
                                '"pipeline" section of the pipe '
                                'file must be boolean.' % key)
                else:
                    if not isinstance(module_description[key], basestring):
                        raise PipelineDescriptionError(
                                'The value of "%s" in the '
                                '"pipeline" section of the pipe '
                                'file must be a string.' % key)

        # Ensure that handles filenames are unique
        n = Counter([
            splitext(basename(m['handles']))[0]
            for m in self.pipe_description['pipeline']
        ])
        repeated = [x for x in n.values() if x > 1]
        if repeated:
            raise PipelineDescriptionError(
                'Handles identifier must be unique.'
            )

        logger.info('pipeline description check successful')

    def check_handles(self):
        '''Check handles structure.
        '''
        lib_path = self.pipe_description.get('lib', None)
        if lib_path:
            self.libpath = self.pipe_description['lib']
            self.libpath = complete_path(
                            self.libpath, self.step_location)
        else:
            if 'JTLIB' in os.environ:
                self.libpath = os.environ['JTLIB']
            else:
                raise ValueError('JTLIB environment variable not set.')

        for i, module in enumerate(self.pipe_description['pipeline']):
            # Check whether executable files exist
            source_path = get_module_path(
                            module['source'], self.libpath)
            if not exists(source_path):
                raise PipelineDescriptionError(
                            'Source file "%s" does not exist.'
                            % source_path)

            # Check whether descriptor files exist
            handles_path = complete_path(
                            module['handles'], self.step_location)

            if not self.handles_descriptions:
                # A description could also be provided from the user interface.
                # In this case .handles files may not exist.
                if not exists(handles_path):
                    raise PipelineDescriptionError(
                            'Handles file "%s" does not exist.' % handles_path)

                # The user interface requires that all handles files
                # have the certain suffix and are stored in a folder called
                # "handles".
                handle_basename = splitext(basename(handles_path))
                handle_dirname = dirname(handles_path)
                if not handle_basename == HANDLES_SUFFIX:
                    logger.warning(
                            'Handles file "%s" should have suffix "%s"',
                            handles_path, HANDLES_SUFFIX)
                if not re.search(r'handles$', handle_dirname):
                    logger.warning(
                            'Handles file "%s" should reside in a '
                            'folder called "handles".', handles_path)

                try:
                    handles = yaml.load(open(handles_path).read())
                except Exception as e:
                    raise PipelineDescriptionError(
                            'Could not read handles file "%s".\n'
                            'Error message:\n%s' % (module['handles'], str(e)))

            else:
                handles = self.handles_descriptions[i]

            required_keys = {'input', 'output'}
            possible_keys = required_keys.union()
            for key in required_keys:
                if key not in handles:
                    raise PipelineDescriptionError(
                                'Handles file "%s" must contain the key "%s".'
                                % (handles_path, key))
                elif key == 'input':
                    if not handles[key]:
                        raise PipelineDescriptionError(
                                'The value of "%s" in handles file "%s" '
                                'cannot be empty.' % (key, handles_path))
                    if not isinstance(handles[key], list):
                        raise PipelineDescriptionError(
                                'The value of "%s" in handles file "%s" '
                                'must be a list.' % (key, handles_path))

            for key in handles:
                if key not in possible_keys:
                    raise PipelineDescriptionError(
                                'Possible keys in handles file "%s" are: "%s"'
                                % (handles_path, '" or "'.join(possible_keys)))

            n = len(set(([o['name'] for o in handles['input']])))
            if n < len(handles['input']):
                raise PipelineDescriptionError(
                            'Names of input items in handles file "%s" '
                            'must be unique.' % handles_path)

            REQUIRED_HANDLE_ITEM_KEYS = {'name', 'type'}
            for j, input_item in enumerate(handles['input']):
                logger.debug(
                    'check input item #%d in handles file "%s"',
                    j, handles_path
                )
                for key in REQUIRED_HANDLE_ITEM_KEYS:
                    if key not in input_item:
                        raise PipelineDescriptionError(
                            'Input #%d in handles file "%s" misses required '
                            'key "%s"' % (j, handles_path, key)
                        )
                try:
                    input_handle = create_handle(**input_item)
                except AttributeError as error:
                    raise PipelineDescriptionError(
                        'Value of "type" of input item #%d named "%s" '
                        'in handles file "%s" specifies an invalid type:\n%s'
                        % (j, input_item['name'], handles_path, str(error))
                    )
                except TypeError as error:
                    raise PipelineDescriptionError(
                        'Input item #%d named "%s" in handles file "%s" is '
                        'not specified correctly:\n%s'
                        % (j, input_item['name'], handles_path, str(error))
                    )
                except Exception:
                    raise

            n = len(set(([o['name'] for o in handles['output']])))
            if n < len(handles['output']):
                raise PipelineDescriptionError(
                    'Names of output items in handles file "%s" '
                    'must be unique.' % handles_path
                )

            for j, output_item in enumerate(handles['output']):
                logger.debug(
                    'check output item #%d in handles file "%s"',
                    j, handles_path
                )
                for key in REQUIRED_HANDLE_ITEM_KEYS:
                    if key not in output_item:
                        raise PipelineDescriptionError(
                            'Output #%d in handles file "%s" misses required '
                            'key "%s"' % (j, handles_path, key)
                        )
                try:
                    output_handle = create_handle(**output_item)
                except AttributeError as error:
                    logger.error('handles description check failed')
                    raise PipelineDescriptionError(
                        'Value of "type" of output item #%d named "%s" '
                        'in handles file "%s" specifies an invalid type:\n%s'
                        % (j, output_item['name'], handles_path, str(error))
                    )
                except TypeError as error:
                    logger.error('handles description check failed')
                    raise PipelineDescriptionError(
                        'Output item #%d named "%s" in handles file "%s" is '
                        'not specified correctly:\n%s'
                        % (j, output_item['name'], handles_path, str(error))
                    )
                except Exception:
                    logger.error('handles description check failed')
                    raise

        logger.info('handles descriptions check successful')

    def check_pipeline_io(self):
        '''Ensures that piped module inputs are actually generated by modules
        upstream in the pipeline.
        '''
        upstream_outputs = list()
        for i, module in enumerate(self.pipe_description['pipeline']):
            handles_path = complete_path(
                module['handles'], self.step_location
            )
            with YamlReader(handles_path) as f:
                if self.handles_descriptions is None:
                    handles = f.read()
                else:
                    handles = self.handles_descriptions[i]

            # Ensure that names of piped arguments are unique
            n = Counter([arg['name'] for arg in handles['input']])
            repeated = [x for x in n.values() if x > 1]
            if repeated:
                raise PipelineDescriptionError(
                    'Names of input items in handles file "%s" '
                    'must be unique.' % handles_path
                )

            if not handles['output']:
                continue
            n = Counter([arg['name'] for arg in handles['output']])
            repeated = [x for x in n.values() if x > 1]
            if repeated:
                raise PipelineDescriptionError(
                    'Names of output items in handles file "%s" '
                    'must be unique.' % handles_path
                )

            for j, input_item in enumerate(handles['input']):
                input_handle = create_handle(**input_item)
                if not isinstance(input_handle, PipeHandle):
                    # We only check piped arguments
                    continue
                channels = self.pipe_description['input']['channels']
                if channels:
                    layer_names = [ch['name'] for ch in channels]
                    if input_handle.key in layer_names:
                        # Only check piped data
                        continue
                    if not module['active']:
                        # Don't check inactive modules
                        continue
                    if input_handle.key not in upstream_outputs:
                        raise PipelineDescriptionError(
                            'The value of "key" of input item #%d '
                            'with name "%s" in handles file "%s" '
                            'is not created upstream in the pipeline: '
                            '\n"%s"'
                            % (j, input_handle.name, handles_path,
                               input_handle.key)
                        )
                else:
                    raise PipelineDescriptionError(
                        'You provided no input for the pipeline.'
                    )

            # Store all upstream output items
            for output_item in handles['output']:
                if 'key' in output_item:
                    output = output_item['key']
                    upstream_outputs.append(output)
        logger.info('pipeline IO check successful')

    def check_all(self):
        '''Checks pipeline and handles descriptions and check module IO logic.
        '''
        self.check_pipeline()
        self.check_handles()
        self.check_pipeline_io()
