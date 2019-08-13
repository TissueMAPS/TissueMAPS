# Copyright (C) 2019 University of Zurich.
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
'''Jterator module for measuring intensity statistics.'''
import collections

VERSION = '0.1.0'

Output = collections.namedtuple('Output', ['label_image'])


def main(input_image, plot=False):
    '''
    Takes in an `intensity_image` (i.e., a TissueMAPS input image) and
    re-uses it as a `label_image` (i.e., pixels belonging to the same
    object have the same unique non-zero integer value).

    Nothing is changed in the input image: it already needs to be a
    label image, e.g.  a label image created in cellprofiler and
    uploaded to TissueMaps.

    Parameters
    ----------
    input_image: numpy.ndarray[int32]
        intensity image that should be re-used as a label image
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    jtmodules.label.Output[Union[numpy.ndarray, str]]
    '''
    return Output(input_image)
