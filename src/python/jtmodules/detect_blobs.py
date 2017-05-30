# Copyright 2016 Markus D. Herrmann, Scott Berry, University of Zurich
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
'''Jterator module for detection of blobs in images.'''
import sep
import numpy as np
import mahotas as mh
import collections
import logging
from jtlib.segmentation import detect_blobs

from jtlib.filter import log_2d

VERSION = '0.5.0'

logger = logging.getLogger(__name__)

Output = collections.namedtuple('Output', ['centroids', 'blobs', 'figure'])


def main(image, mask, threshold=1, min_area=5, mean_area=5, plot=False):
    '''Detects blobs in `image` using an implementation of
    `SExtractor <http://www.astromatic.net/software/sextractor>`_ [1].
    The `image` is first convolved with a Laplacian of Gaussian filter of size
    `mean_area` to enhance blob-like structures. The enhanced image is
    then thresholded at `threshold` level and connected pixel components are
    subsequently deplended.

    Parameters
    ----------
    image: numpy.ndarray[Union[numpy.uint8, numpy.uint16]]
        grayscale image in which blobs should be detected
    mask: numpy.ndarray[Union[numpy.int32, numpy.bool]]
        binary or labeled image that masks pixel regions in which blobs
        should be detected
    threshold: int, optional
        factor by which pixel values in the convolved image must be above
        background to be considered part of a blob (default: ``1``)
    min_area: int, optional
        minimal size a blob is allowed to have (default: ``5``)
    mean_area: int, optional
        estimated average size of a blob (default: ``5``)
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    jtmodules.detect_blobs.Output[Union[numpy.ndarray, str]]

    References
    ----------
    .. [1] Bertin, E. & Arnouts, S. 1996: SExtractor: Software for source
    extraction, Astronomy & Astrophysics Supplement 317, 393
    '''

    logger.info('detect blobs above threshold {0}'.format(threshold))
    blobs, centroids = detect_blobs(
        image=image, mask=mask, threshold=threshold, min_area=min_area
    )

    n = np.unique(blobs[blobs>0])

    logger.info('%d blobs detected', n)

    if plot:
        logger.info('create plot')
        from jtlib import plotting
        colorscale = plotting.create_colorscale(
            'Spectral', n=n, permute=True, add_background=True
        )
        plots = [
            plotting.create_intensity_image_plot(
                image, 'ul', clip=True
            ),
            plotting.create_mask_image_plot(
                blobs, 'ur', colorscale=colorscale
            )
        ]
        figure = plotting.create_figure(
            plots,
            title='detected #{0} blobs above threshold {1}'.format(n, threshold)
        )
    else:
        figure = str()

    return Output(centroids, blobs, figure)

