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
'''Jterator module for rasterizing objects onto a label image.'''
import logging
import numpy as np
import collections
import mahotas as mh
from jtlib.utils import label

logger = logging.getLogger(__name__)

VERSION = '0.1.0'

Output = collections.namedtuple('Output', ['label_image', 'figure'])


def main(objects, plot=False):
    '''Rasterizes objects onto a label image, i.e. assigns to all pixels of a
    connected component an identifier number that is unique for each object
    in the image.

    Parameters
    ----------
    objects: numpy.ndarray[int32]
        label image with objects
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    jtmodules.label.Output[Union[numpy.ndarray, str]]
    '''
    label_image = objects
    if plot:
        from jtlib import plotting
        plots = [
            plotting.create_mask_image_plot(label_image, 'ur')
        ]
        figure = plotting.create_figure(plots, title='Labeled image')
    else:
        figure = str()

    return Output(label_image, figure)
