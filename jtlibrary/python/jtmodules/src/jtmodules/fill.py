# Copyright (C) 2016 University of Zurich.
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
'''Jterator module for filling holes in connected pixel components.'''
import logging
import numpy as np
import collections
import mahotas as mh

logger = logging.getLogger(__name__)

VERSION = '0.0.2'

Output = collections.namedtuple('Output', ['filled_mask', 'figure'])


def main(mask, plot=False):
    '''Fills holes in connected pixel components.

    Parameters
    ----------
    mask: numpy.ndarray[numpy.bool]
        binary image that should filled
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    jtmodules.fill.Output[Union[numpy.ndarray, str]]

    '''
    filled_mask = mh.close_holes(mask, np.ones((3, 3), bool))

    if plot:
        from jtlib import plotting
        plots = [
            plotting.create_mask_image_plot(mask, 'ul'),
            plotting.create_mask_image_plot(filled_mask, 'ur')
        ]
        figure = plotting.create_figure(plots, title='Labeled image')
    else:
        figure = str()

    return Output(filled_mask, figure)
