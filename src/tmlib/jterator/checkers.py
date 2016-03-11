import yaml
import re
import os
import logging
from os.path import splitext, basename, exists, dirname
from collections import Counter
from . import path_utils
from .project import HANDLE_SUFFIX
from ..readers import YamlReader
from ..errors import PipelineDescriptionError

logger = logging.getLogger(__name__)


class PipelineChecker(object):
    '''
    Class for checking pipeline and handle descriptions.
    '''

    def __init__(self, project_dir, pipe_description,
                 handles_descriptions=None):
        '''
        Initialize an instance of class JtChecker.

        Parameters
        ----------
        project_dir: str
            path to Jterator project folder
        pipe_description: dict
            pipeline description (module order)
        handles_descriptions: dict, optional
            list of module descriptions (module input/output)
        '''
        self.pipe_description = pipe_description
        self.handles_descriptions = handles_descriptions
        self.project_dir = project_dir

    def check_pipeline(self):
        '''
        Check pipeline structure.
        '''
        # Check "project" section
        if 'description' not in self.pipe_description.keys():
            raise PipelineDescriptionError(
                    'Pipeline file must contain the key "description".')
        if 'lib' in self.pipe_description.keys():
            libpath = self.pipe_description['lib']
            libpath = path_utils.complete_path(libpath, self.project_dir)
            if libpath:
                if not exists(libpath):
                    raise PipelineDescriptionError(
                            'The path defined by "lib" in your '
                            'pipeline file is not valid.')
        # Check "jobs" section
        if 'input' not in self.pipe_description.keys():
            raise PipelineDescriptionError(
                    'Pipe file must contain the key "input".')
        possible_keys = {'channels', 'objects'}
        for i, key in enumerate(self.pipe_description['input'].keys()):
            if key not in possible_keys:
                raise PipelineDescriptionError(
                    'Pipe file must contain one of the following keys '
                    'as a subkey of "inputs": "%s"'
                    % ", ".join(possible_keys))

            if not isinstance(self.pipe_description['input'][key], list):
                raise PipelineDescriptionError(
                        'The value of "%s" in the "inputs" section '
                        'of the pipe file must be a list.' % key)
            # Check for presence of required keys
            required_subkeys = {'name'}
            possible_subkeys = required_subkeys.union({'correct', 'align'})
            inputs = self.pipe_description['input'][key]
            if inputs:
                for inpt in inputs:
                    for k in required_subkeys:
                        if k not in inpt:
                            raise PipelineDescriptionError(
                                    'Each element of "%s" in the "inputs" '
                                    'section of the pipe file requires '
                                    'key "%s".' % (key, k))
                    for k in inpt:
                        if k not in possible_subkeys:
                            raise PipelineDescriptionError(
                                    'Unknown key "%s" for element #%d of "%s" '
                                    'in "inputs" section of the pipe file.'
                                    % (k, i, key))

        # Check "pipeline" section
        if 'pipeline' not in self.pipe_description.keys():
            raise PipelineDescriptionError(
                    'Pipeline file must contain the key "pipeline".')
        if not isinstance(self.pipe_description['pipeline'], list):
            raise PipelineDescriptionError(
                    'The value of "pipeline" in the pipe file must be a list.')

        required_subkeys = {'handle', 'source', 'active'}
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
        n = Counter([splitext(basename(m['handle']))[0]
                    for m in self.pipe_description['pipeline']])
        repeated = [x for x in n.values() if x > 1]
        if repeated:
            raise PipelineDescriptionError(
                                'Handles identifier must be unique.')

        logger.info('pipeline description check successful')

    def check_handles(self):
        '''
        Check handles structure.
        '''
        lib_path = self.pipe_description.get('lib', None)
        if lib_path:
            self.libpath = self.pipe_description['lib']
            self.libpath = path_utils.complete_path(
                            self.libpath, self.project_dir)
        else:
            if 'JTLIB' in os.environ:
                self.libpath = os.environ['JTLIB']
            else:
                raise ValueError('JTLIB environment variable not set.')

        for i, module in enumerate(self.pipe_description['pipeline']):
            # Check whether executable files exist
            source_path = path_utils.get_module_path(
                            module['source'], self.libpath)
            if not exists(source_path):
                raise PipelineDescriptionError(
                            'Source file "%s" does not exist.'
                            % source_path)

            # Check whether descriptor files exist
            handle_path = path_utils.complete_path(
                            module['handle'], self.project_dir)

            if not self.handles_descriptions:
                # A description could also be provided from the user interface.
                # In this case .handles files may not exist.
                if not exists(handle_path):
                    raise PipelineDescriptionError(
                            'Handle file "%s" does not exist.' % handle_path)

                # The user interface requires that all handles files
                # have the certain suffix and are stored in a folder called
                # "handles".
                handle_basename = splitext(basename(handle_path))
                handle_dirname = dirname(handle_path)
                if not handle_basename == HANDLE_SUFFIX:
                    logger.warning(
                            'Handle file "%s" should have suffix "%s"',
                            handle_path, HANDLE_SUFFIX)
                if not re.search(r'handles$', handle_dirname):
                    logger.warning(
                            'Handle file "%s" should reside in a '
                            'folder called "handles".', handle_path)

                try:
                    handle = yaml.load(open(handle_path).read())
                except Exception as e:
                    raise PipelineDescriptionError(
                            'Could not read handle file "%s".\n'
                            'Error message:\n%s' % (module['handle'], str(e)))

            else:
                handle = self.handles_descriptions[i]

            required_keys = {'input', 'output'}
            possible_keys = required_keys.union()
            for key in required_keys:
                if key not in handle:
                    raise PipelineDescriptionError(
                                'Handle file "%s" must contain the key "%s".'
                                % (handle_path, key))
                elif key == 'input':
                    if not handle[key]:
                        raise PipelineDescriptionError(
                                'The value of "%s" in handle file "%s" '
                                'cannot be empty.' % (key, handle_path))
                    if not isinstance(handle[key], list):
                        raise PipelineDescriptionError(
                                'The value of "%s" in handle file "%s" '
                                'must be a list.' % (key, handle_path))

            for key in handle:
                if key not in possible_keys:
                    raise PipelineDescriptionError(
                                'Possible keys in handle file "%s" are: "%s"'
                                % (handle_path, '" or "'.join(possible_keys)))

            required_subkeys = {'name', 'value', 'mode', 'kind'}
            possible_subkeys = required_subkeys.union({'help', 'options'})
            possible_modes = {'pipe', 'store', 'constant'}
            possible_kinds = {
                'constant': {'scalar', 'sequence'},
                'store': {'coordinates', 'features', 'attribute'},
                'pipe': {'image'}
            }
            for j, input_item in enumerate(handle['input']):
                for key in required_subkeys:
                    if key not in input_item:
                        raise PipelineDescriptionError(
                                    'Input argument #%d in handles file "%s" '
                                    'misses required key "%s".'
                                    % (j, handle_path, key))
                mode = input_item['mode']
                for key in input_item:
                    if key not in possible_subkeys:
                        raise PipelineDescriptionError(
                                    'Unknown key for input item #%d '
                                    'in handle file "%s".\n'
                                    'Possible keys are: "%s".'
                                    % (j, handle_path,
                                       '" or "'.join(possible_subkeys)))
                    if key == 'mode':
                        if not isinstance(input_item[key], basestring):
                            raise PipelineDescriptionError(
                                    'The value of "%s" of input item #%d '
                                    'in handles file "%s" must be a string.'
                                    % (key, j, handle_path))
                        if input_item[key] not in possible_modes:
                            raise PipelineDescriptionError(
                                    'Unknown mode "%s" for input item #%d '
                                    'in handle file "%s".\n'
                                    'Possible modes for inputs are: "%s"'
                                    % (input_item[key], j, handle_path,
                                       '", "'.join(possible_modes)))
                    elif key == 'kind':
                        if not isinstance(input_item[key], basestring):
                            raise PipelineDescriptionError(
                                    'The value of "%s" of input item #%d '
                                    'in handles file "%s" must be a string.'
                                    % (key, j, handle_path))
                        if input_item[key] not in possible_kinds[mode]:
                            raise PipelineDescriptionError(
                                    'Unknown kind "%s" for input item '
                                    '#%d in handle file "%s".\n'
                                    'Possible kinds for inputs are: "%s"'
                                    % (input_item[key], j, handle_path,
                                       '", "'.join(possible_kinds[mode])))
                    elif key == 'value':
                        if not input_item[key]:
                            continue  # allow to be empty
                        if not (isinstance(input_item[key], str) or
                                isinstance(input_item[key], int) or
                                isinstance(input_item[key], float) or
                                isinstance(input_item[key], list)):
                            raise PipelineDescriptionError(
                                    'The value of "%s" of input item #%d '
                                    'in handles file "%s" must be either '
                                    'a string, a number, or '
                                    'a list of strings/numbers.'
                                    % (key, j, handle_path))

            required_subkeys = {'name', 'mode', 'kind'}
            possible_subkeys = possible_subkeys.union({'ref', 'id'})
            if not handle['output']:
                continue  # allow to be empty
            for j, output_item in enumerate(handle['output']):
                for key in required_subkeys:
                    if key not in output_item:
                        raise PipelineDescriptionError(
                                    'Output argument #%d in handles file "%s" '
                                    'misses required key "%s".'
                                    % (j, handle_path, key))
                mode = output_item['mode']
                for key in output_item:
                    if key not in possible_subkeys:
                        raise PipelineDescriptionError(
                                    'Unknown keys for output item #%d '
                                    'in handle file "%s".\n'
                                    'Possible keys are: "%s".'
                                    % (j, handle_path,
                                       '" or "'.join(possible_subkeys)))
                    if key == 'mode':
                        if not isinstance(output_item[key], basestring):
                            raise PipelineDescriptionError(
                                    'The value of "%s" of output item #%d '
                                    'in handles file "%s" must be a string.'
                                    % (key, j, handle_path))
                        if output_item[key] not in possible_modes:
                            raise PipelineDescriptionError(
                                    'Unknown mode "%s" for output item #%d '
                                    'in handle file "%s".\n'
                                    'Possible modes for outputs are: "%s".'
                                    % (output_item[key], j, handle_path,
                                       '", "'.join(possible_modes)))
                        if output_item[key] == 'pipe':
                            if 'id' not in output_item:
                                raise PipelineDescriptionError(
                                    'Output item #%d in handle file "%s" '
                                    'has mode "pipe" and thus '
                                    'requires key "id".'
                                    % (j, handle_path))
                    elif key == 'kind':
                        if not isinstance(output_item[key], basestring):
                            raise PipelineDescriptionError(
                                    'The value of "%s" of output item #%d '
                                    'in handles file "%s" must be a string.'
                                    % (key, j, handle_path))
                        if output_item[key] not in possible_kinds[mode]:
                            raise PipelineDescriptionError(
                                    'Unknown kind "%s" for output item '
                                    '#%d in handle file "%s".\n'
                                    'Possible kinds for inputs are: "%s"'
                                    % (output_item[key], j, handle_path,
                                       '", "'.join(possible_kinds[mode])))
                    elif key == 'ref':
                        if not isinstance(output_item[key], basestring):
                            raise PipelineDescriptionError(
                                    'The value of "%s" of output item #%d '
                                    'in handles file "%s" must be a string.'
                                    % (key, j, handle_path))
                        if output_item.get('mode', 'constant') != 'store':
                            raise PipelineDescriptionError(
                                    'Value of "mode" for output item #%d '
                                    'in handle file "%s" must be "store" '
                                    'to be able to specify "%s".'
                                    % (j, handle_path, key))
                        arg_names = [arg['name'] for arg in handle['input']]
                        if output_item[key] not in arg_names:
                            raise PipelineDescriptionError(
                                    'The value of "%s" for output item #%d '
                                    'in handle file "%s" must match a '
                                    '"name" of one of the input items.'
                                    % (key, j, handle_path,
                                       '", "'.join(possible_kinds)))
                    elif key == 'id':
                        if not isinstance(output_item[key], basestring):
                            raise PipelineDescriptionError(
                                    'The value of "%s" of output item #%d '
                                    'in handles file "%s" must be a string.'
                                    % (key, j, handle_path))

            # Ensure that handles filenames are unique
            n = Counter([o['name'] for o in handle['output']])
            repeated = [x for x in n.values() if x > 1]
            if repeated:
                raise PipelineDescriptionError('Output names must be unique.')

        logger.info('handle descriptions check successful')

    def check_pipeline_io(self):
        '''
        Ensure that piped module inputs are actually generated by modules
        upstream in the pipeline.
        '''
        upstream_outputs = list()
        with YamlReader() as reader:
            for i, module in enumerate(self.pipe_description['pipeline']):
                handle_path = path_utils.complete_path(
                                module['handle'], self.project_dir)
                if self.handles_descriptions is None:
                    handle = reader.read(handle_path)
                else:
                    handle = self.handles_descriptions[i]

                # Ensure that names of piped arguments are unique
                n = Counter([arg['name'] for arg in handle['input']])
                repeated = [x for x in n.values() if x > 1]
                if repeated:
                    raise PipelineDescriptionError(
                            'Names of input items in handle file "%s" '
                            'must be unique.' % handle_path)

                if not handle['output']:
                    continue
                n = Counter([arg['name'] for arg in handle['output']])
                repeated = [x for x in n.values() if x > 1]
                if repeated:
                    raise PipelineDescriptionError(
                            'Names of output items in handle file "%s" '
                            'must be unique.' % handle_path)

                for j, input_item in enumerate(handle['input']):
                    if (input_item['mode'] != 'pipe' or
                            input_item['value'] is None):
                        # We only check piped arguments
                        continue
                    name = input_item['value']
                    channels = self.pipe_description['input']['channels']
                    if channels:
                        layer_names = [ch['name'] for ch in channels]
                        if name in layer_names:
                            # These names are written into the HDF5 file by
                            # the program and are therefore not created
                            # upstream in the pipeline.
                            continue
                        if not module['active']:
                            # Don't check inactive modules
                            continue
                        if input_item['value'] not in upstream_outputs:
                            raise PipelineDescriptionError(
                                    'The value of "value" of input item #%d '
                                    'with name "%s" in handle file "%s" '
                                    'is not created upstream in the pipeline: '
                                    '\n"%s"'
                                    % (j, input_item['name'], handle_path,
                                       input_item['value']))

                # Store all upstream output items
                for output_item in handle['output']:
                    if 'id' in output_item:
                        output = output_item['id']
                        upstream_outputs.append(output)
        logger.info('pipeline IO check successful')

    def check_all(self):
        '''
        Check pipeline and handles descriptions and check module IO logic.
        '''
        self.check_pipeline()
        self.check_handles()
        self.check_pipeline_io()
