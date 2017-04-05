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
'''Jterator module for inverting an image.'''
import logging
import numpy as np
import collections

VERSION = '0.0.1'

logger = logging.getLogger(__name__)

Output = collections.namedtuple('Output', ['inverted_image', 'figure'])


def main(image, plot=False):
    '''Inverts `image`.

    Parameters
    ----------
    image: numpy.ndarray[Union[numpy.uint8, numpy.uint16, numpy.bool, numpy.int32]]
        image that should be inverted
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    jtmodules.invert.Output[Union[numpy.ndarray, str]]

    Note
    ----
    In case `image` is a label image with type ``numpy.int32`` it is binarized
    (casted to ``numpy.bool``) before inversion.
    '''
    if image.dtype == np.int32:
        logger.info('binarize label image before inversion')
        image = image > 0
    logger.info('invert image')
    inverted_image = np.invert(image)

    if plot:
        logger.info('create plot')
        from jtlib import plotting
        if str(image.dtype).startswith('uint'):
            data = [
                plotting.create_intensity_image_plot(
                    image, 'ul', clip=True,
                ),
                plotting.create_intensity_image_plot(
                    inverted_image, 'ur', clip=True,
                ),
            ]
        else:
            data = [
                plotting.create_mask_image_plot(
                    image, 'ul', clip=True,
                ),
                plotting.create_mask_image_plot(
                    inverted_image, 'ur', clip=True,
                ),
            ]
        figure = plotting.create_figure(
            data, title='original and inverted image'
        )
    else:
        figure = str()

    return Output(inverted_image, figure)
