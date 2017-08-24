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
import logging
import collections
import sep
import numpy as np
import mahotas as mh

from jtlib.segmentation import detect_blobs
from jtlib.filter import log_2d

VERSION = '0.6.0'

logger = logging.getLogger(__name__)

Output = collections.namedtuple('Output', ['centroids', 'blobs', 'figure'])


def main(image, mask, threshold=1, min_area=3, mean_area=5, max_area=1000,
        clip_percentile=99.999, plot=False):
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
        binary or labeled image that specifies pixel regions of interest
        in which blobs should be detected
    threshold: int, optional
        threshold level for pixel values in the convolved image
        (default: ``1``)
    min_area: int, optional
        minimal size a blob is allowed to have (default: ``3``)
    mean_area: int, optional
        estimated average size of a blob (default: ``5``)
    max_area: int, optional
        maximal size a blob is allowed to have to be subject to deblending;
        no attempt will be made to deblend blobs larger than `max_area`
        (default: ``100``)
    clip_percentile: float, optional
        clip intensity values in `image` above the given percentile; this may
        help in attenuating artifacts
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

    detect_image = image.copy()

    p = np.percentile(image, clip_percentile)
    detect_image[image > p] = p

    # Enhance the image for blob detection by convoling it with a LOG filter
    f = -1 * log_2d(size=mean_area, sigma=float(mean_area - 1)/3)
    detect_image = mh.convolve(detect_image.astype(float), f)
    detect_image[detect_image < 0] = 0

    # Mask regions of too big blobs
    pre_blobs = mh.label(detect_image > threshold)[0]
    bad_blobs, n_bad = mh.labeled.filter_labeled(pre_blobs, min_size=max_area)
    logger.info(
        'remove {0} blobs because they are bigger than {1} pixels'.format(
            n_bad, max_area
        )
    )
    detect_mask = np.invert(mask > 0)
    detect_mask[bad_blobs > 0] = True
    detect_image[bad_blobs > 0] = 0

    logger.info('deblend blobs')
    blobs, centroids = detect_blobs(
        image=detect_image, mask=detect_mask, threshold=threshold,
        min_area=min_area
    )

    n = len(np.unique(blobs[blobs>0]))

    logger.info('{0} blobs detected'.format(n))

    if plot:
        logger.info('create plot')
        from jtlib import plotting

        colorscale = plotting.create_colorscale(
            'Spectral', n=n, permute=True, add_background=True
        )
        plots = [
            plotting.create_float_image_plot(
                detect_image, 'ul', clip=True
            ),
            plotting.create_mask_image_plot(
                blobs, 'ur', colorscale=colorscale
            )
        ]
        figure = plotting.create_figure(
            plots,
            title=(
                'detected #{0} blobs above threshold {1}'
                ' in LOG filtered image'.format(n, threshold)
            )
        )
    else:
        figure = str()

    return Output(centroids, blobs, figure)

