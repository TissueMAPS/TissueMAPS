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
import yaml
import pytest
import inspect
import importlib


def _check_module_structure(name):
    module = importlib.import_module('jtmodules.%s' % name)
    functions = inspect.getmembers(module, predicate=inspect.isfunction)
    function_names = [f[0] for f in functions]
    assert 'main' in function_names, (
        'Module "%s" must implement a "main" function' % name
    )
    # TODO: VERSION


def _check_existence_of_docs(name):
    module = importlib.import_module('jtmodules.%s' % name)
    assert module.__doc__ is not None, (
        'Documentation for module "%s" missing' % name
    )
    functions = inspect.getmembers(module, predicate=inspect.isfunction)
    main_func = [f[1] for f in functions if f[0] == 'main'][0]
    assert main_func.__doc__ is not None, (
        'Documentation for "main" function in module "%s" missing'
        % name
    )


def _check_module_parameters(name, handles_filename):
    module = importlib.import_module('jtmodules.%s' % name)
    functions = inspect.getmembers(module, predicate=inspect.isfunction)
    with open(handles_filename, 'r') as f:
        handles_description = yaml.load(f)
    input_handles_names = [h['name'] for h in handles_description['input']]
    for func_name, func in functions:
        if func_name == 'main':
            parameters = inspect.getargspec(func)
            for arg in parameters.args:
                assert arg in input_handles_names, (
                    'Argument "%s" of function "main" in module "%s" '
                    'is not described in corresponding handle file "%s"'
                    % (arg, name, handles_filename)
                )
            for handle_name in input_handles_names:
                assert handle_name in parameters.args, (
                    'Input handle "%s" described in handle file "%s" '
                    'is not an argument of function "main" of module "%s"'
                    % (handle_name, handles_filename, name)
                )


def test_modules_content(modules, handles):
    for name, filename in modules.iteritems():
        if not filename.endswith('.py'):
            continue
        print 'test module "%s"' % name
        _check_module_structure(name)
        _check_existence_of_docs(name)
        _check_module_parameters(name, handles[name])
