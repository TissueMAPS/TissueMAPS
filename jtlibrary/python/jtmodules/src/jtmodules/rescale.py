# Copyright (C) 2017 University of Zurich.
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
'''Jterator module for rescaling an image between two values'''
import numpy as np
import collections
import logging

VERSION = '0.1.0'

Output = collections.namedtuple('Output', ['rescaled_image', 'figure'])

logger = logging.getLogger(__name__)

def main(intensity_image, min_value=None, max_value=None, plot=False):
    '''Rescales an image between `min_value` and `max_value`.

    Parameters
    ----------
    intensity_image: numpy.ndarray[Union[numpy.uint8, numpy.uint16]]
        grayscale image
    min: int, optional
        grayscale value to be set as zero in rescaled image (default:
        ``False``)
    max: int, optional
        grayscale value to be set as max in rescaled image (default:
        ``False``)
    plot: bool, optional
        whether a figure should be created (default: ``False``)
    '''

    rescaled_image = np.zeros(shape=intensity_image.shape,
                              dtype=np.int32)

    if min_value is not None:
        logger.info('subtract min_value %s', min_value)
        rescaled_image = intensity_image.astype(np.int32) - min_value
        rescaled_image[rescaled_image < 0] = 0
    else:
        rescaled_image = intensity_image

    if max_value is not None:
        logger.info('set max_value %s', max_value)

        max_for_type = np.iinfo(intensity_image.dtype).max
        rescaled_image = rescaled_image.astype(np.float32) / max_value * max_for_type
        rescaled_image[rescaled_image > max_for_type] = max_for_type

    rescaled_image = rescaled_image.astype(intensity_image.dtype)

    if plot:
        logger.info('create plot')
        from jtlib import plotting
        plots = [
            plotting.create_intensity_image_plot(
                intensity_image, 'ul', clip=True),
            plotting.create_intensity_image_plot(
                rescaled_image, 'ur', clip=True)
        ]
        figure = plotting.create_figure(plots, title='rescaled image')
    else:
        figure = str()

    return Output(rescaled_image, figure)
