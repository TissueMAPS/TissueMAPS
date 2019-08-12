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

Output = collections.namedtuple('Output', ['label_image', 'figure'])


def main(input_image, plot=False):
    '''Takes in an `intensity_image` and converts it to a `label_image` (not
    changing anything in the image => it already needs to be a label image, e.g.
    a label image created in cellprofiler and uploaded to TissueMaps).

    Parameters
    ----------
    input_image: numpy.ndarray[int32]
        intensity image that should be converted to a label image
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    jtmodules.label.Output[Union[numpy.ndarray, str]]


    '''
    if plot:
        figure = f.plot()
    else:
        figure = str()

    return Output(input_image, figure)
