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
'''Jterator module for combining objects from two binary mask images into one.
'''
import numpy as np
import logging
import collections

logger = logging.getLogger(__name__)

VERSION = '0.0.1'

Output = collections.namedtuple('Output', ['output_mask', 'figure'])


def main(input_mask_1, input_mask_2, plot=False):
    '''Combines two binary masks, such that the resulting combined mask
    is ``True`` where either `input_mask_1` OR `input_mask_2` is ``True``.

    Parameters
    ----------
    input_mask_1: numpy.ndarray[numpy.bool]
        2D binary array
    input_mask_2: numpy.ndarray[numpy.bool]
        2D binary array

    Returns
    -------
    jtmodules.combine_objects.Output

    '''
    combined_mask = np.logical_or(input_mask_1, input_mask_2)

    output_mask = combined_mask
    if plot:
        from jtlib import plotting
        plots = [
            plotting.create_mask_image_plot(input_mask_1, 'ul'),
            plotting.create_mask_image_plot(input_mask_2, 'ur'),
            plotting.create_mask_image_plot(combined_mask, 'll')
        ]
        figure = plotting.create_figure(plots, title='combined mask')
    else:
        figure = str()

    return Output(output_mask, figure)

