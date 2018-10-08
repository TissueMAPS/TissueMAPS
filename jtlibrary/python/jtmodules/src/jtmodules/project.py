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
'''Jterator module for making a projection along the final dimension of the
 array'''
import collections
import logging
import numpy as np

VERSION = '0.1.0'

Output = collections.namedtuple('Output', ['projected_image', 'figure'])

logger = logging.getLogger(__name__)

projections = {
    'max': np.max,
    'sum': np.sum
}

def main(image, method='max', plot=False):
    '''Projects an image along the last dimension using the given `method`.

    Parameters
    ----------
    image: numpy.ndarray[Union[numpy.uint8, numpy.uint16]]
        grayscale image
    method: str, optional
        method used for projection
        (default: ``"max"``, options: ``{"max", "sum"}``)
    plot: bool, optional
        whether a figure should be created (default: ``False``)
    '''
    logger.info('project image using "%s" method', method)
    func = projections[method]
    projected_image = func(image, axis=-1)

    projected_image = projected_image.astype(image.dtype)

    if plot:
        logger.info('create plot')
        from jtlib import plotting
        plots = [
	    plotting.create_intensity_image_plot(
                projected_image, 'ul', clip=True
            )
	]
        figure = plotting.create_figure(plots, title='projection image')
    else:
        figure = str()

    return Output(projected_image, figure)
