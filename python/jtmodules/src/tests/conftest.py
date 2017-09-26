# Copyright 2016 Markus D. Herrmann, University of Zurich
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
import pytest
import os
import glob
from tmlib.workflow.jterator.project import HANDLES_SUFFIX


@pytest.fixture(scope='session')
def handles():
    '''A `pytest` fixture that provides the name and absolute path to
    each available *.handles.yaml* file.

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
    each available module file (Python: *.py*, Matlab: *.m* and R: *.r*)
    in the language-specific *jtmodules* packages.

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
