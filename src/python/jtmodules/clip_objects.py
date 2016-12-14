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
'''Jterator module for clipping objects to create new objects
that consist of the set of non-intersecting pixels.
'''
import numpy as np
import collections

VERSION = '0.0.1'

Output = collections.namedtuple('Output', ['clipped_image', 'figure'])


def main(image_1, image_2, plot=False):
    '''Clips a labeled image using another image as a mask, such that
    intersecting pixels/voxels are set to background.

    Parameters
    ----------
    image_1: numpy.ndarray[numpy.int32]
        label image that should be clipped
    image_2: numpy.ndarray[numpy.int32]
        intersecting label image that should be used for clipping
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    jtmodules.clip_objects.Output

    Note
    ----
    `image_1` and `image_2` must have the same size

    Raises
    ------
    ValueError
        when `image_1` and `image_2` don't have the same dimensions
        and data type and if they don't have unsigned integer type
    '''
    if image_1.shape != image_2.shape:
        raise ValueError('Both images must have the same dimensions.')
    clipped_image = np.copy(image_1)
    clipped_image[image_2 > 0] = 0

    if plot:
        from jtlib import plotting
        n_objects = len(np.unique(clipped_image)[1:])
        colorscale = plotting.create_colorscale(
            'Spectral', n=n_objects, permute=True, add_background=True
        )
        plots = [
            plotting.create_mask_image_plot(
                image_1, 'ul', colorscale=colorscale
            ),
            plotting.create_mask_image_plot(
                image_2, 'ur', colorscale=colorscale
            ),
            plotting.create_mask_image_plot(
                clipped_image, 'll', colorscale=colorscale
            )
        ]
        figure = plotting.create_figure(plots, title='clipped image')
    else:
        figure = str()

    return Output(clipped_image, figure)
