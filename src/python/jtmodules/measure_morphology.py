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
'''Jterator module for measuring morphological features (size and shape).'''
import collections
import jtlib.features

VERSION = '0.0.1'

Output = collections.namedtuple('Output', ['measurements', 'figure'])


def main(label_image, plot=False):
    '''Measures morphological features for objects in `label_image`.

    Parameters
    ----------
    label_image: numpy.ndarray[int32]
        label image with objects that should be measured
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    jtmodules.measure_morphology.Output

    See also
    --------
    class:`jtlib.features.Morphology`
    '''
    f = jtlib.features.Morphology(label_image=label_image)

    measurements = [f.extract()]

    if plot:
        figure = f.plot()
    else:
        figure = str()

    return Output(measurements, figure)
