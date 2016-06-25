import pytest
import os
import glob
from tmlib.workflow.jterator.project import HANDLES_SUFFIX


@pytest.fixture(scope='session')
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


@pytest.fixture(scope='session')
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
