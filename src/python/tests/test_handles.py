import os
import glob
import yaml
import pytest
import inspect
from tmlib.workflow.jterator.project import HANDLES_SUFFIX
import tmlib.workflow.jterator.handles as handles_types


@pytest.fixture(scope='module')
def handles():
    '''A `pytest` fixture that provides the name and absolute path to
    each available handles file.

    Returns
    -------
    Dict[str, str]
        name and path to handle file
    '''
    handles_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '../../../handles')
    )
    files = glob.glob(os.path.join(handles_path, '*%s' % HANDLES_SUFFIX))
    names = [os.path.basename(f).split('.')[0] for f in files]
    return dict(zip(names, files))


@pytest.fixture(scope='module')
def modules():
    '''A `pytest` fixture that provides the name and absolute path to
    each available module file in the `jtmodules` package.

    Returns
    -------
    Dict[str, str]
        name and path to module file
    '''
    py_modules_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '../jtmodules')
    )
    m_modules_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '../../matlab/+jtmodules')
    )
    r_modules_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '../../r/jtmodules/R')
    )
    py_files = [
        f for f in glob.glob(os.path.join(py_modules_path, '*.py'))
        if '__init__.py' not in f
    ]
    m_files = glob.glob(os.path.join(m_modules_path, '*.m'))
    r_files = glob.glob(os.path.join(m_modules_path, '*.r'))
    files = py_files + m_files + r_files
    names = [
        os.path.splitext(os.path.basename(f))[0] for f in files
    ]
    return dict(zip(names, files))


def test_existance_of_handles_files(handles, modules):
    for name in modules.keys():
        error_message = 'No handles file for module "%s" found.' % name
        assert name in handles.keys(), error_message


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


def test_handles_structure(handles):
    for name, filename in handles.iteritems():
        required_keys = {'input', 'output'}
        with open(filename, 'r') as f:
            description = yaml.load(f)
            for k in required_keys:
                assert k in description, (
                    'Handles description in file "%s" doesn\'t have required '
                    'key "%s"' % (filename, k)
                )
                assert isinstance(description[k], list), (
                    '%s in handles file "%s" must be an array.'
                    % (k.capitalize(), filename)
                )


def test_handles_description(handles):
    def _check_handle(index, description, filename, group):
        assert hasattr(handles_types, description['type']), (
            'Type "%s" of %s handle #%d in file "%s" is not valid.'
            % (description['type'], group, index, filename)
        )
        Handle = getattr(handles_types, description['type'])
        parameters = inspect.getargspec(Handle.__init__)
        index_defaults = len(parameters.args[1:]) - len(parameters.defaults)
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

    for name, filename in handles.iteritems():
        with open(filename, 'r') as f:
            description = yaml.load(f)
            for i, h in enumerate(description['input']):
                _check_handle(i, h, filename, 'input')
            for i, h in enumerate(description['output']):
                _check_handle(i, h, filename, 'output')

