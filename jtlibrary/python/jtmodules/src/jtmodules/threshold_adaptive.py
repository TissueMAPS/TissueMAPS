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
from jtlib.utils import rescale_to_8bit
from scipy.ndimage import generic_filter

logger = logging.getLogger(__name__)

VERSION = '0.2.0'

Output = collections.namedtuple('Output', ['mask', 'figure'])


def main(image, method, kernel_size, constant=0,
        min_threshold=None, max_threshold=None, plot=False):
    '''Thresholds an image with a locally adaptive threshold method.

    Parameters
    ----------
    image: numpy.ndarray
        grayscale image that should be thresholded
    method: str
        thresholding method (options: ``{"crosscorr", "niblack"}``)
    kernel_size: int
        size of the neighbourhood region that's used to calculate the threshold
        value at each pixel position (must be an odd number)
    constant: Union[float, int], optional
        depends on `method`; in case of ``"crosscorr"`` method the constant
        is subtracted from the computed weighted sum per neighbourhood region
        and in case of ``"niblack"`` the constant is multiplied by the
        standard deviation and this term is then subtracted from the mean
        computed per neighbourhood region
    min_threshold: int, optional
        minimal threshold level (default: ``numpy.min(image)``)
    max_threshold: int, optional
        maximal threshold level (default: ``numpy.max(image)``)
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    jtmodules.threshold_adaptive.Output

    Raises
    ------
    ValueError
        when `kernel_size` is not an odd number or when `method` is not valid

    Note
    ----
    Typically requires prior filtering to reduce noise in the image.

    References
    ----------
    .. [1] Niblack, W. 1986: An introduction to Digital Image Processing, Prentice-Hall.
    '''
    if kernel_size % 2 == 0:
        raise ValueError('Argument "kernel_size" must be an odd integer.')
    logger.debug('set kernel size: %d', kernel_size)

    if max_threshold is None:
        max_threshold = np.max(image)
    logger.debug('set maximal threshold: %d', max_threshold)

    if min_threshold is None:
        min_threshold = np.min(image)
    logger.debug('set minimal threshold: %d', min_threshold)

    logger.debug('map image intensities to 8-bit range')
    image_8bit = rescale_to_8bit(image, upper=99.99)

    logger.info('threshold image')
    if method == 'crosscorr':
        thresh_image = cv2.adaptiveThreshold(
            image_8bit, maxValue=255,
            adaptiveMethod=cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            thresholdType=cv2.THRESH_BINARY,
            blockSize=kernel_size, C=int(constant)
        )
    elif method == 'niblack':
        thresh_image = cv2.ximgproc.niBlackThreshold(
            image_8bit, maxValue=255, type=cv2.THRESH_BINARY,
            blockSize=kernel_size, delta=constant
        )
    else:
        raise ValueError(
            'Arugment "method" can be one of the following:\n'
            '"crosscorr" or "niblack"'
        )
    # OpenCV treats masks as unsigned integer and not as boolean
    thresh_image = thresh_image > 0

    # Manually fine tune automatic thresholding result
    thresh_image[image < min_threshold] = False
    thresh_image[image > max_threshold] = True

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

