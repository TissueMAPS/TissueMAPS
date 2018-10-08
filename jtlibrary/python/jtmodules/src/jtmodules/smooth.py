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
'''Jterator module for smooting an image with a low-pass filter.

For more information on image filtering see
`OpenCV tutorial <http://opencv-python-tutroals.readthedocs.org/en/latest/py_tutorials/py_smoothed_imageproc/py_filtering/py_filtering.html>`_.


'''
import logging
import cv2
import mahotas as mh
import collections
import skimage.morphology
import skimage.filters.rank
import numpy as np

VERSION = '0.1.0'

logger = logging.getLogger(__name__)

Output = collections.namedtuple('Output', ['smoothed_image', 'figure'])


def main(image, filter_name, filter_size, plot=False):
    '''Smoothes (blurs) `image`.

    Parameters
    ----------
    image: numpy.ndarray
        grayscale image that should be smoothed
    filter_name: str
        name of the filter kernel that should be applied
        (options: ``{"avarage", "gaussian", "median", "bilateral"}``)
    filter_size: int
        size of the kernel
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    jtmodules.smooth.Output[Union[numpy.ndarray, str]]

    Raises
    ------
    ValueError
        when `filter_name` is not
        ``"avarage"``, ``"gaussian"``, ``"median"`` or ``"bilateral"``
    '''
    se = np.ones((filter_size, filter_size))
    if filter_name == 'average':
        logger.info('apply "average" filter')
        smoothed_image = mh.mean_filter(image, se)
    elif filter_name == 'gaussian':
        logger.info('apply "gaussian" filter')
        smoothed_image = mh.gaussian_filter(image, filter_size)
    elif filter_name == 'median':
        logger.info('apply "median" filter')
        smoothed_image = mh.median_filter(image, se)
    elif filter_name == 'bilateral':
        smoothed_image = cv2.bilateralFilter(
            image.astype(np.float32), d=0,
            sigmaColor=filter_size, sigmaSpace=filter_size
        ).astype(image.dtype)
    else:
        raise ValueError(
            'Arugment "filter_name" can be one of the following:\n'
            '"average", "gaussian", "median" or "bilateral"'
        )
    smoothed_image = smoothed_image.astype(image.dtype)

    if plot:
        logger.info('create plot')
        from jtlib import plotting
        clip_value = np.percentile(image, 99.99)
        data = [
            plotting.create_intensity_image_plot(
                image, 'ul', clip=True, clip_value=clip_value
            ),
            plotting.create_intensity_image_plot(
                smoothed_image, 'ur', clip=True, clip_value=clip_value
            ),
        ]
        figure = plotting.create_figure(
            data,
            title='Smoothed with "{0}" filter (kernel size: {1})'.format(
                filter_name, filter_size
            )
        )
    else:
        figure = str()

    return Output(smoothed_image, figure)
