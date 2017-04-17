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
'''Jterator module for detection of blobs in images.'''
import sep
import numpy as np
import mahotas as mh
import collections
import logging

VERSION = '0.4.0'

logger = logging.getLogger(__name__)

sep.set_extract_pixstack(10**7)

Output = collections.namedtuple('Output', ['centroids', 'blobs', 'figure'])


def main(image, mask, threshold=5, min_area=5, plot=False):
    '''Detects blobs in `image` using an implementation of
    `SExtractor <http://www.astromatic.net/software/sextractor>`_ [1].

    Parameters
    ----------
    image: numpy.ndarray[Union[numpy.uint8, numpy.uint16]]
        grayscale image in which blobs should be detected
    mask: numpy.ndarray[Union[numpy.int32, numpy.bool]]
        binary or labeled image that masks pixel regions in which blobs
        should be detected
    threshold: int, optional
        factor by which pixel values must be above background
        to be considered part of a blob (default: ``5``)
    min_area: int, optional
        minimal size of a blob (default: ``5``)
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    jtmodules.detect_blobs.Output[Union[numpy.ndarray, str]]

    References
    ----------
    .. [1] Bertin, E. & Arnouts, S. 1996: SExtractor: Software for source extraction, Astronomy & Astrophysics Supplement 317, 393
    '''

    logger.info('detect blobs above threshold {0}'.format(threshold))
    detection, blobs = sep.extract(
        image.astype('float'), threshold, mask=np.invert(mask>0),
        minarea=min_area, segmentation_map=True,
        deblend_nthresh=500, deblend_cont=0,
        filter_kernel=None, clean=False
    )

    n = len(detection)

    centroids = np.zeros(image.shape, dtype=np.int32)
    y = detection['y'].astype(int)
    x = detection['x'].astype(int)
    # WTF? In rare cases object coorindates lie outside of the image.
    y[y > image.shape[0]] = image.shape[0]
    x[x > image.shape[1]] = image.shape[1]
    centroids[y, x] = np.arange(1, n + 1)

    centroids[mask] = 0
    mh.labeled.relabel(centroids, inplace=True)

    blobs[mask] = 0
    mh.labeled.relabel(blobs, inplace=True)

    n = np.max(blobs)
    logger.info('%d blobs detected', len(detection))

    if plot:
        logger.info('create plot')
        from jtlib import plotting
        colorscale = plotting.create_colorscale(
            'Spectral', n=n, permute=True, add_background=True
        )
        plots = [
            plotting.create_intensity_overlay_image_plot(
                image, mh.morph.dilate(centroids>0), 'ul', clip=True
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
