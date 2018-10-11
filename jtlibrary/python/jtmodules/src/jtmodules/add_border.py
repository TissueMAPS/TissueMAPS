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

Output = collections.namedtuple('Output', ['enlarged_image', 'figure'])

logger = logging.getLogger(__name__)

def main(intensity_image, border_size=0, plot=False):
    '''Adds a border to an image

    Parameters
    ----------
    intensity_image: numpy.ndarray[Union[numpy.uint8, numpy.uint16]]
        grayscale image
    border_size: int, optional
        size of border (default: 0)
    plot: bool, optional
        whether a figure should be created (default: ``False``)
    '''

    enlarged_image = np.zeros(shape=(intensity_image.shape[0] + 2*border_size, intensity_image.shape[1] + 2*border_size),
                              dtype=intensity_image.dtype);

    enlarged_image[border_size:(border_size + intensity_image.shape[0]), border_size:(border_size + intensity_image.shape[1])] = intensity_image

    if plot:
        logger.info('create plot')
        from jtlib import plotting
        plots = [
            plotting.create_intensity_image_plot(
                intensity_image, 'ul', clip=True),
            plotting.create_intensity_image_plot(
                enlarged_image, 'ur', clip=True)
        ]
        figure = plotting.create_figure(plots, title='enlarged image')
    else:
        figure = str()

    return Output(enlarged_image, figure)
