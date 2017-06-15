# Copyright 2017 Markus D. Herrmann, Scott Berry, University of Zurich
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
import logging
import numpy as np
import mahotas as mh
import sep


logger = logging.getLogger(__name__)


def detect_blobs(image, mask, threshold, min_area, deblend_nthresh=500,
        deblend_cont=0):
    '''Detects blobs in `image` using an implementation of
    `SExtractor <http://www.astromatic.net/software/sextractor>`_ [1].

    Parameters
    ----------
    image: numpy.ndarray[Union[numpy.uint8, numpy.uint16]]
        grayscale image in which blobs should be detected
    mask: numpy.ndarray[numpy.bool]
        binary image that masks pixel regions in which no blobs should be
        detected
    threshold: int, optional
        factor by which pixel values must be above background
        to be considered part of a blob (default: ``5``)
    min_area: int, optional
        minimal size of a blob
    deblend_ntresh: int, optional
        number of deblending thresholds (default: ``500``)
    deblend_cont: int, optional
        minimum contrast ratio for deblending (default: ``0``)

    Returns
    -------
    Tuple[numpy.ndarray[numpy.int32]]
        detected blobs and the corresponding centroids

    References
    ----------
    .. [1] Bertin, E. & Arnouts, S. 1996: SExtractor: Software for source
    extraction, Astronomy & Astrophysics Supplement 317, 393
    '''
    sep.set_extract_pixstack(10**7)

    img = image.astype('float')

    # We pad the image with mirrored pixels to prevent border artifacts.
    pad = 50
    left = img[:, 1:pad]
    right = img[:, -pad:-1]
    detect_img = np.c_[np.fliplr(left), img, np.fliplr(right)]
    upper = detect_img[1:pad, :]
    lower = detect_img[-pad:-1, :]
    detect_img = np.r_[np.flipud(upper), detect_img, np.flipud(lower)]

    logger.info('detect blobs via thresholding and deblending')
    detection, blobs = sep.extract(
        detect_img, threshold,
        minarea=min_area, segmentation_map=True,
        deblend_nthresh=deblend_nthresh, deblend_cont=deblend_cont,
        filter_kernel=None, clean=False
    )

    centroids = np.zeros(detect_img.shape, dtype=np.int32)
    y = detection['y'].astype(int)
    x = detection['x'].astype(int)
    # WTF? In rare cases object coorindates lie outside of the image.
    n = len(detection)
    y[y > detect_img.shape[0]] = detect_img.shape[0]
    x[x > detect_img.shape[1]] = detect_img.shape[1]
    centroids[y, x] = np.arange(1, n + 1)

    # Remove the padded border pixels
    blobs = blobs[pad-1:-(pad-1), pad-1:-(pad-1)].copy()
    centroids = centroids[pad-1:-(pad-1), pad-1:-(pad-1)].copy()

    # Blobs detected outside of regions of interest are discarded.
    blobs[mask > 0] = 0
    blobs[mh.bwperim(np.invert(mask)) > 0] = 0
    mh.labeled.relabel(blobs, inplace=True)

    # We need to ensure that centroids are labeled the same way as blobs.
    centroids[centroids > 0] = blobs[centroids > 0]

    return (blobs, centroids)
