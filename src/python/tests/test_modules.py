import yaml
import pytest
import inspect
import importlib


def check_module_structure(module):
    functions = inspect.getmembers(module, predicate=inspect.isfunction)
    function_names = [f[0] for f in functions]
    assert 'main' in function_names, (
        'Module "%s" must implement a function called "main"' % module.__name__
    )
    # TODO: VERSION


def check_existence_of_docs(module):
    assert module.__doc__ is not None, (
        'Documentation for module "%s" missing' % module.__name__
    )
    functions = inspect.getmembers(module, predicate=inspect.isfunction)
    main_func = [f[1] for f in functions if f[0] == 'main'][0]
    assert main_func.__doc__ is not None, (
        'Documentation for "main" function in module "%s" missing'
        % module.__name__
    )


def check_module_parameters(module, handles_filename):
    functions = inspect.getmembers(module, predicate=inspect.isfunction)
    handles_filename = handles[module.__name__]
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
                    % (arg, module.__name__, handles_filename)
                )
            for handle_name in input_handles_names:
                assert handle_name in parameters.args, (
                    'Input handle "%s" described in handle file "%s" '
                    'is not an argument of function "main" of module "%s"'
                    % (handle_name, handles_filename, module.__name__)
                )


def test_modules_content(modules):
    for name, filename in modules.iteritems():
        if not filename.endswith('.py'):
            continue
        print 'test module "%s"' % name
        module = importlib.import_module('jtmodules.%s' % name)
        check_module_structure(module)
        check_existence_of_docs(module)
        check_module_parameters(module)
