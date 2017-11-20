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
'''Jterator module for expanding objects by a constant number of pixels.'''
import scipy.ndimage as ndi
import collections

VERSION = '0.0.1'

Output = collections.namedtuple('Output', ['expanded_image', 'figure'])


def main(image, n, plot=False):
    '''Expands objects in `image` by `n` pixels along each axis.

    Parameters
    ----------
    image: numpy.ndarray[numpy.int32]
        2D label image with objects that should be expanded
    n: int
        number of pixels by which each connected component should be expanded
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    jtmodules.expand_objects.Output
    '''
    # NOTE: code from CellProfiler module "expandorshrink"
    background = image == 0
    distance, (i, j) = ndi.distance_transform_edt(background, return_indices=True)
    expanded_image = image.copy()
    mask = background & (distance < n)
    expanded_image[mask] = image[i[mask], j[mask]]

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
        figure = plotting.create_figure(plots, title='expanded image')
    else:
        figure = str()

    return Output(expanded_image, figure)
