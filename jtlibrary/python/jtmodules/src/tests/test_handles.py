# Copyright (C) 2016 University of Zurich.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import yaml
import pytest
import inspect
import tmlib.workflow.jterator.handles as handles_types


def test_existance_of_handles_files(handles, modules):
    for name in modules.keys():
        assert name in handles.keys(), (
            'No handles file for module "%s" found.' % name
        )


def test_handles_yaml_syntax(handles):
    for name, filename in handles.iteritems():
        with open(filename, 'r') as f:
            try:
                yaml.load(f)
            except yaml.error.YAMLError as err:
                error_message = (
                    'Handles file "%s" doesn\'t have correct YAML syntax:\n%s'
                    % (filename, str(err))
                )
                pytest.fail(error_message)
            except:
                raise


def _check_handles_structure(description, filename):
    required_keys = {'input', 'output'}
    for k in required_keys:
        assert k in description, (
            'Handles description in file "%s" doesn\'t have required '
            'key "%s"' % (filename, k)
        )
        assert isinstance(description[k], list), (
            '%s in handles file "%s" must be an array.'
            % (k.capitalize(), filename)
        )


def _check_handles_input_output(description, filename):
    for i, h in enumerate(description['input']):
        _check_handle(i, h, filename, 'input')
    for i, h in enumerate(description['output']):
        _check_handle(i, h, filename, 'output')


def _check_handle(index, description, filename, group):
    assert hasattr(handles_types, description['type']), (
        'Type "%s" of %s handle #%d in file "%s" is not valid.'
        % (description['type'], group, index, filename)
    )
    Handle = getattr(handles_types, description['type'])
    parameters = inspect.getargspec(Handle.__init__)
    index_defaults = len(parameters.args[1:])
    if parameters.defaults is not None:
         index_defaults -= len(parameters.defaults)
    for i, arg in enumerate(parameters.args[1:]):
        if i >= index_defaults:
            continue
        assert arg in description, (
            'Description of %s handle #%d in file "%s" requires key "%s"'
            % (group, index, filename, param)
        )
    for key in description.keys():
        if key == 'type':
            continue
        assert key in parameters.args, (
            'Invalid key "%s" in description of %s handle #%d in file "%s"'
            % (key, group, index, filename)
        )


def test_handles_content(handles):
    for name, filename in handles.iteritems():
        print 'test handles "%s"' % name
        with open(filename, 'r') as f:
            description = yaml.load(f)
        _check_handles_structure(description, filename)
        _check_handles_input_output(description, filename)

