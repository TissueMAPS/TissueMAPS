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
'''Jterator module for thresholding of an image using an automatically
determined global threshold level.
'''
import logging
import collections
import mahotas as mh
import numpy as np

logger = logging.getLogger(__name__)

VERSION = '0.0.2'

Output = collections.namedtuple('Output', ['mask', 'figure'])


def main(image, correction_factor=1, min_threshold=None, max_threshold=None,
        plot=False):
    '''Thresholds an image by applying an automatically determined global
    threshold level using
    `Otsu's method <https://en.wikipedia.org/wiki/Otsu%27s_method>`_.

    Additional parameters allow correction of the calculated threshold
    level or restricting it to a defined range. This may be useful to prevent
    extreme levels in case the `image` contains artifacts. Setting
    `min_threshold` and `max_threshold` to the same value results in a
    manual thresholding.

    Parameters
    ----------
    image: numpy.ndarray[numpy.uint8 or numpy.unit16]
        grayscale image that should be thresholded
    correction_factor: int, optional
        value by which the calculated threshold level will be multiplied
        (default: ``1``)
    min_threshold: int, optional
        minimal threshold level (default: ``numpy.min(image)``)
    max_threshold: int, optional
        maximal threshold level (default: ``numpy.max(image)``)
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    jtmodules.threshold_otsu.Output[Union[numpy.ndarray, str]]
    '''
    if max_threshold is None:
        max_threshold = np.max(image)
    logger.debug('set maximal threshold: %d', max_threshold)

    if min_threshold is None:
        min_threshold = np.min(image)
    logger.debug('set minimal threshold: %d', min_threshold)
    logger.debug('set threshold correction factor: %.2f', correction_factor)

    threshold = mh.otsu(image)
    logger.info('calculated threshold level: %d', threshold)

    corr_threshold = threshold * correction_factor
    logger.info('corrected threshold level: %d', corr_threshold)

    if corr_threshold > max_threshold:
        logger.info('set threshold level to maximum: %d', max_threshold)
        corr_threshold = max_threshold
    elif corr_threshold < min_threshold:
        logger.info('set threshold level to minimum: %d', min_threshold)
        corr_threshold = min_threshold

    logger.info('threshold image at %d', corr_threshold)
    mask = image > corr_threshold

    if plot:
        logger.info('create plot')
        from jtlib import plotting
        outlines = mh.morph.dilate(mh.labeled.bwperim(mask))
        plots = [
            plotting.create_intensity_overlay_image_plot(
                image, outlines, 'ul'
            ),
            plotting.create_mask_image_plot(mask, 'ur')
        ]
        figure = plotting.create_figure(
            plots, title='thresholded at %s' % corr_threshold
        )
    else:
        figure = str()

    return Output(mask, figure)
