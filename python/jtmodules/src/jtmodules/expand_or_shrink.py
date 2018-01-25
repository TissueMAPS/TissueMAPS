# Copyright 2016-2018 Markus D. Herrmann & Scott Berry, University of Zurich
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
'''Jterator module for expanding or shrinking objects by a constant number of pixels.'''
import scipy.ndimage as ndi
import numpy as np
import collections
import logging

VERSION = '0.1.1'

logger = logging.getLogger(__name__)

Output = collections.namedtuple('Output', ['expanded_image', 'figure'])


def main(image, n, plot=False):
    '''Expands objects in `image` by `n` pixels along each axis.

    Parameters
    ----------
    image: numpy.ndarray[numpy.int32]
        2D label image with objects that should be expanded or shrunk
    n: int
        number of pixels by which each connected component should be
        expanded or shrunk
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    jtmodules.expand_objects.Output
    '''
    # NOTE: code from CellProfiler module "expandorshrink"
    # NOTE (S.B. 25.1.2018): renamed from "expand" to "expand_or_shrink"
    expanded_image = image.copy()
    if (n > 0):
        logger.info('expanding objects by %d pixels',n)
        background = image == 0
        distance, (i, j) = ndi.distance_transform_edt(
            background, return_indices=True
        )
        mask = background & (distance < n)
        expanded_image[mask] = image[i[mask], j[mask]]

    elif (n < 0):
        logger.info('shrinking objects by %d pixels',abs(n))
        print 'shrinking'
        objects = image != 0
        distance = ndi.distance_transform_edt(
            objects, return_indices=False
        )
        mask = np.invert(distance > abs(n))
        expanded_image[mask] = 0

    if plot:
        from jtlib import plotting
        n_objects = len(np.unique(expanded_image)[1:])
        colorscale = plotting.create_colorscale(
            'Spectral', n=n_objects, permute=True, add_background=True
        )
        plots = [
            plotting.create_mask_image_plot(
                image, 'ul', colorscale=colorscale
            ),
            plotting.create_mask_image_plot(
                expanded_image, 'ur', colorscale=colorscale
            )
        ]
        figure = plotting.create_figure(
            plots,
            title='expanded image'
        )
    else:
        figure = str()

    return Output(expanded_image, figure)
