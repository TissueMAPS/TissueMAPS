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
'''Jterator module for measuring weighted Hu texture features.'''
import collections
import jtlib.features

VERSION = '0.0.1'


def main(label_image, intensity_image, plot=False):
    '''Measures texture features for objects in `label_image` based on
    grayscale values in `intensity_image`.

    Parameters
    ----------
    label_image: numpy.ndarray[int32]
        label image with objects that should be measured
    intensity_image: numpy.ndarray[unit8 or uint16]
        grayscale image
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    Dict[str, List[pandas.DataFrame[float]] or str]
        * "measurements": extracted Hu features
        * "figure": JSON string in case `plot` is ``True``

    See also
    --------
    :class:`jtlib.features.Hu`
    '''
    f = jtlib.features.Hu(
        label_image=label_image, intensity_image=intensity_image
    )

    outputs = {'measurements': [f.extract()]}

    if plot:
        outputs['figure'] = f.plot()
    else:
        outputs['figure'] = str()

    return outputs
