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
'''Jterator module for thresholding an image with a locally adaptive method,
where different thresholds are applied to different regions of the image.

For more information on adaptive thresholding please refer to the
`OpenCV documentation <http://docs.opencv.org/trunk/d7/d4d/tutorial_py_thresholding.html>`.
'''
import logging
import collections
import mahotas as mh
import cv2
import numpy as np

logger = logging.getLogger(__name__)

VERSION = '0.1.0'

Output = collections.namedtuple('Output', ['mask', 'figure'])


def main(image, kernel_size, offset=0, plot=False):
    '''Thresholds an image with a locally adaptive threshold, where locality
    is defined by `kernel_size`.

    Parameters
    ----------
    image: numpy.ndarray
        grayscale image that should be thresholded
    kernel_size: int
        size of the neighbourhood region that's used to calculate the threshold
        value at each pixel position (must be an odd number)
    offset: int, optional
        offset that is added to the mean calculated per neighbourhood region
        (may be positive or negative)
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    jtmodules.threshold_adaptive.Output

    Raises
    ------
    ValueError
        when `kernel_size` is not an odd number
    '''
    if kernel_size % 2 == 0:
        raise ValueError('Argument "kernel_size" must be an odd integer.')
    logger.debug('set kernel size: %d', kernel_size)

    logger.debug('map image intensities to 8-bit range')
    image_8bit = mh.stretch(image)

    logger.info('threshold image')
    thresh_image = cv2.adaptiveThreshold(
        image_8bit, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,
        kernel_size, offset
    )
    # OpenCV treats masks as unsigned integer and not as boolean
    thresh_image = thresh_image > 0

    if plot:
        logger.info('create plot')
        from jtlib import plotting
        outlines = mh.morph.dilate(mh.labeled.bwperim(thresh_image))
        plots = [
            plotting.create_intensity_overlay_image_plot(
                image, outlines, 'ul'
            ),
            plotting.create_mask_image_plot(thresh_image, 'ur')
        ]
        figure = plotting.create_figure(
            plots,
            title='thresholded adaptively with kernel size: %d' % kernel_size
        )
    else:
        figure = str()

    return Output(thresh_image, figure)

