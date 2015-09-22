#!/usr/bin/env python
# encoding: utf-8

import yaml
import re
from os.path import splitext, basename, exists, dirname
from collections import Counter
import warnings
from . import path_utils
from .. import utils
from ..errors import PipelineDescriptionError


def JteratorWarning(msg, *a):
    '''
    Custom warning message that will end up in standard error.
    '''
    return 'Warning: ' + str(msg) + '\n'

warnings.formatwarning = JteratorWarning


class PipelineChecker(object):
    '''
    Class for checking pipeline and module descriptions.
    '''

    def __init__(self, project_dir, pipe_description,
                 handles_descriptions=None):
        '''
        Initialize an instance of class JtChecker.

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

            {
                'project': {
                    'name': str,
                    'libpath': str
                },

                'jobs': {
                    'folder': str,
                    'pattern': [
                            {
                                'name': str,
                                'expression': str
                            },               
                            ...
                    ]
                    }
                },

                'pipeline': [
                        {
                            'active': bool,
                            'handles': str,
                            'module': str
                        },
                        ...
                ]

            }
        '''
        # Check "project" section
        if 'project' not in self.pipe_description.keys():
            raise PipelineDescriptionError(
                    'Pipeline file must contain the key "project".')
        if 'lib' in self.pipe_description['project'].keys():
            libpath = self.pipe_description['project']['lib']
            libpath = path_utils.complete_path(libpath, self.project_dir)
            if not exists(libpath):
                raise PipelineDescriptionError(
                        'The path defined by "lib" in your '
                        'pipeline description is not valid.')
        # Check "jobs" section
        if 'images' not in self.pipe_description.keys():
            raise PipelineDescriptionError(
                    'Pipe file must contain the key "images".')
        if 'layers' not in self.pipe_description['images'].keys():
            raise PipelineDescriptionError(
                    'Pipe file must contain the key "layers" '
                    'as a subkey of "images".')
        if not isinstance(self.pipe_description['images']['layers'], list):
            raise PipelineDescriptionError(
                    'The value of "layers" in the "images" section '
                    'of the pipe file must be a list.')

        # Check for presence of required keys
        required_subkeys = ['name']
        for pattern_description in self.pipe_description['images']['layers']:
            for key in required_subkeys:
                if key not in pattern_description:
                    raise PipelineDescriptionError(
                            'Each element of "layers" in the "images" section '
                            'in the pipe file requires a key "%s".' % key)

        # Check "pipeline" section
        if 'pipeline' not in self.pipe_description.keys():
            raise PipelineDescriptionError(
                    'Pipeline file must contain the key "pipeline".')
        if not isinstance(self.pipe_description['pipeline'], list):
            raise PipelineDescriptionError(
                    'The value of "pipeline" in the pipe file must be a list.')

        required_subkeys = ['handles', 'module', 'active']
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
        n = Counter([splitext(basename(m['handles']))[0]
                    for m in self.pipe_description['pipeline']])
        repeated = [x for x in n.values() if x > 1]
        if repeated:
            raise PipelineDescriptionError('Handles files need to be unique.')

        print('🍺  Pipe description check successful!')

    def check_handles(self):
        '''
        Check handles structure.

            {
                'input': [
                    {
                        'name': str,
                        'value': int or str or float or
                                 List[int] or List[str] or List[float],
                        'class': str 
                    },

                    ...

                ],

                'output': [
                    {
                        'name': str,
                        'value': int or str or float or
                                 List[int] or List[str] or List[float],
                        'class': str
                    },

                    ...

                ],

                'plot': bool
            }
        '''
        self.libpath = self.pipe_description['project']['lib']
        self.libpath = path_utils.complete_path(self.libpath, self.project_dir)
        for i, module in enumerate(self.pipe_description['pipeline']):
            # Check whether executable files exist
            module_path = path_utils.complete_module_path(
                            module['module'], self.libpath, self.project_dir)
            if not exists(module_path):
                raise PipelineDescriptionError(
                        'Module file "%s" does not exist.' % module_path)

            # Check whether descriptor files exist
            handles_path = path_utils.complete_module_path(
                            module['handles'], self.libpath, self.project_dir)

            if not self.handles_descriptions:
                # A description could also be provided from the user interface.
                # In this case .handles files may not exist.
                if not exists(handles_path):
                    raise PipelineDescriptionError(
                            'Handles file "%s" does not exist.'
                            % module['handles'])

                # The user interface requires that all handles files
                # have the .handles suffix and are stored in a folder called
                # "handles".
                handles_basename = splitext(basename(handles_path))
                handles_dirname = dirname(handles_path)
                if not handles_basename[1] == '.handles':
                    warnings.warn('Handles file "%s" doesn\'t have suffix '
                                  '".handles". This may cause problems with '
                                  'the user interface.' % handles_path)
                if not re.search(r'handles$', handles_dirname):
                    warnings.warn('Handles file "%s" doesn\'t reside in a '
                                  'foler called "handles". This may cause '
                                  'problems with the user interface.'
                                  % handles_path)

                try:
                    handles = yaml.load(open(handles_path).read())
                except Exception as e:
                    raise PipelineDescriptionError(
                            'Could not read handles file "%s".\n'
                            'Error message:\n%s' % (module['handles'], str(e)))

            else:
                handles = self.handles_descriptions[i]

            # Check "input" section
            required_keys = ['input', 'output', 'plot']
            for key in required_keys:
                if key not in handles:
                    raise PipelineDescriptionError(
                            'Handles file must contain the key "%s".' % key)
                if key == 'plot':
                    if not isinstance(handles[key], bool):
                        raise PipelineDescriptionError(
                                'The value of "%s" in the '
                                '"input" section of the handles '
                                'file must be boolean.' % key)
                elif key == 'input':
                    if not isinstance(handles[key], list):
                        raise TypeError(
                                'The value of "%s" in the '
                                '"input" section of the handles '
                                'file must be a list.' % key)

            required_subkeys = ['name', 'value', 'class']
            for input_arg in handles['input']:
                for key in required_subkeys:
                    if key not in input_arg:
                        raise PipelineDescriptionError(
                                'Input argument in handles file '
                                '"%s" misses required key "%s".'
                                % (handles_path, key))
                    if key == 'class':
                        class_options = ['pipeline', 'parameter']
                        if input_arg[key] not in class_options:
                            raise PipelineDescriptionError(
                                    'The input value of "%s" in the '
                                    'handles file must be either %s'
                                    % ' or '.join(class_options))
                    if key == 'value':
                        if not input_arg[key]:
                            continue  # allow to be empty
                        if not (isinstance(input_arg[key], str) or
                                isinstance(input_arg[key], int) or
                                isinstance(input_arg[key], float) or
                                isinstance(input_arg[key], list)):
                            raise TypeError(
                                    '"Value" of input argument "%s" in "%s"'
                                    'must be either a string, a number, or '
                                    'a list of strings/numbers.'
                                    % (input_arg['name'], handles_path))

            # Check "output" section
            if not handles['output']:
                continue  # allow to be empty
            for output_arg in handles['output']:
                for key in required_subkeys:
                    if key not in output_arg:
                        raise PipelineDescriptionError(
                                'Output argument in handles file '
                                '"%s" misses required key "%s".'
                                % (handles_path, key))
                    if key == 'class':
                        if output_arg[key] != 'pipeline':
                            raise PipelineDescriptionError(
                                    'The output value of "%s" in handles'
                                    'file must be in "pipeline".')

            # Ensure that handles filenames are unique
            n = Counter([o['name'] for o in handles['output']])
            repeated = [x for x in n.values() if x > 1]
            if repeated:
                raise PipelineDescriptionError(
                        'Output names need to be unique.')

            if not isinstance(handles['plot'], bool):
                raise PipelineDescriptionError(
                        'Plot argument in handles file '
                        '"%s" needs to be boolean.' % handles_path)

        print('🍺  Handles descriptions check successful!')

    def check_pipeline_io(self):
        '''
        Ensure that module inputs have been produced upstream in the pipeline.
        '''
        outputs = list()
        for i, module in enumerate(self.pipe_description['pipeline']):
            handles_path = path_utils.complete_module_path(
                            module['handles'], self.libpath, self.project_dir)
            if self.handles_descriptions is None:
                handles = utils.read_yaml(handles_path)
            else:
                handles = self.handles_descriptions[i]

            # Ensure that argument names are unique
            n = Counter([arg['name'] for arg in handles['input']])
            repeated = [x for x in n.values() if x > 1]
            if repeated:
                raise PipelineDescriptionError(
                        'Input arguments names in "%s" '
                        'have to be unique.' % handles_path)
            if not handles['output']:
                continue
            n = Counter([arg['name'] for arg in handles['output']])
            repeated = [x for x in n.values() if x > 1]
            if repeated:
                raise PipelineDescriptionError(
                        'Output arguments names in "%s" '
                        'have to be unique.' % handles_path)

            # Check pipeline logic:
            # Check whether input arguments for current module were produced
            # upstream in the pipeline
            for input_arg in handles['input']:
                if (input_arg['class'] != 'pipeline'
                        or input_arg['value'] is None):
                    # We only check for non-empty data passed via the HDF5 file
                    continue
                name = input_arg['value']
                layer_names = [
                    layer['name']
                    for layer in self.pipe_description['images']['layers']
                ]
                if name in layer_names:
                    # These names are written into the HDF5 file by Jterator
                    # and are therefore not created in the pipeline.
                    # So there is no need to check them here.
                    continue
                if input_arg['value'] not in outputs:
                    raise PipelineDescriptionError(
                            'Input "%s" of module "%s" is not '
                            'created upstream in the pipeline.'
                            % (input_arg['name'], module['handles']))

            # Store all upstream output arguments
            for output_arg in handles['output']:
                output = output_arg['value']
                outputs.append(output)
        print('🍺  Module input/output check successful!')

    def check_all(self):
        self.check_pipeline()
        self.check_handles()
        self.check_pipeline_io()
