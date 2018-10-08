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
'''Jterator module for clipping objects to create new objects
that consist of the set of non-intersecting pixels.
'''
import numpy as np
import mahotas as mh
import collections

VERSION = '0.1.0'

Output = collections.namedtuple('Output', ['clipped_image', 'figure'])


def main(image, clipping_mask, plot=False):
    '''Clips a labeled image using another image as a mask, such that
    intersecting pixels/voxels are set to background.

    Parameters
    ----------
    image: numpy.ndarray
        image that should be clipped
    clipping_mask: numpy.ndarray[numpy.int32 or numpy.bool]
        image that should be used as clipping mask
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    jtmodules.clip_objects.Output

    Raises
    ------
    ValueError
        when `image` and `clipping_mask` don't have the same dimensions
    '''
    if image.shape != clipping_mask.shape:
        raise ValueError(
            '"image" and "clipping_mask" must have the same dimensions'
        )
    clipping_mask = clipping_mask > 0

    clipped_image = image.copy()
    clipped_image[clipping_mask] = 0

    if plot:
        from jtlib import plotting
        if str(image.dtype).startswith('uint'):
            plots = [
                plotting.create_intensity_image_plot(
                    image, 'ul', clip=True
                ),
                plotting.create_mask_image_plot(
                    clipping_mask, 'ur'
                ),
                plotting.create_intensity_image_plot(
                    clipped_image, 'll', clip=True
                )
            ]
        else:
            n_objects = len(np.unique(image)[1:])
            colorscale = plotting.create_colorscale(
                'Spectral', n=n_objects, permute=True, add_background=True
            )
            plots = [
                plotting.create_mask_image_plot(
                    image, 'ul', colorscale=colorscale
                ),
                plotting.create_mask_image_plot(
                    clipping_mask, 'ur'
                ),
                plotting.create_mask_image_plot(
                    clipped_image, 'll', colorscale=colorscale
                )
            ]
        figure = plotting.create_figure(plots, title='clipped image')
    else:
        figure = str()

    return Output(clipped_image, figure)
