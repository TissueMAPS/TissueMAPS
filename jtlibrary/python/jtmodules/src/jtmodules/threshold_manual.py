
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
'''Jterator module for thresholding of an image using a given global threshold
level.
'''
import logging
import collections
import mahotas as mh
import numpy as np

logger = logging.getLogger(__name__)

VERSION = '0.0.1'

Output = collections.namedtuple('Output', ['mask', 'figure'])


def main(image, threshold, plot=False):
    '''Thresholds an image by applying a given global threshold level.

    Parameters
    ----------
    image: numpy.ndarray
        image of arbitrary data type that should be thresholded
    threshold: int
        threshold level
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    jtmodules.threshold_manual.Output[Union[numpy.ndarray, str]]
    '''
    logger.info('threshold image at %d', threshold)
    mask = image > threshold

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
            plots, title='thresholded at %s' % threshold
        )
    else:
        figure = str()

    return Output(mask, figure)
