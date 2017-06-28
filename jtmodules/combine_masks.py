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
'''Jterator module for combining objects from two binary mask images into one
by performing an element-wise logical OR operation.
'''
import numpy as np
import logging
import collections

logger = logging.getLogger(__name__)

VERSION = '0.0.1'

Output = collections.namedtuple('Output', ['combined_mask', 'figure'])


def main(mask_1, mask_2, plot=False):
    '''Combines two binary masks, such that the resulting combined mask
    is ``True`` where either `mask_1` OR `mask_2` is ``True``.

    Parameters
    ----------
    mask_1: numpy.ndarray[numpy.bool]
        2D binary array
    mask_2: numpy.ndarray[numpy.bool]
        2D binary array

    Returns
    -------
    jtmodules.combine_objects.Output

    '''
    combined_mask = np.logical_or(mask_1, mask_2)

    if plot:
        from jtlib import plotting
        plots = [
            plotting.create_mask_image_plot(mask_1, 'ul'),
            plotting.create_mask_image_plot(mask_2, 'ur'),
            plotting.create_mask_image_plot(combined_mask, 'll')
        ]
        figure = plotting.create_figure(plots, title='combined mask')
    else:
        figure = str()

    return Output(combined_mask, figure)

