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
import collections
import numpy as np
import mahotas as mh
import sep


def extract_blobs_in_mask(
    image, mask, threshold, min_area, segmentation_map,
        deblend_nthresh, deblend_cont, filter_kernel, clean):
    '''Detects blobs in `image` using an implementation of
    `SExtractor <http://www.astromatic.net/software/sextractor>`_ [1].

    References
    ----------
    .. [1] Bertin, E. & Arnouts, S. 1996: SExtractor: Software for source
    extraction, Astronomy & Astrophysics Supplement 317, 393
    '''
    sep.set_extract_pixstack(10**7)

    detection, blobs = sep.extract(
        image.astype('float'), threshold, mask=np.invert(mask > 0),
        minarea=min_area, segmentation_map=segmentation_map,
        deblend_nthresh=deblend_nthresh, deblend_cont=deblend_cont,
        filter_kernel=filter_kernel, clean=clean
    )

    n = len(detection)

    centroids = np.zeros(image.shape, dtype=np.int32)
    y = detection['y'].astype(int)
    x = detection['x'].astype(int)
    # WTF? In rare cases object coorindates lie outside of the image.
    y[y > image.shape[0]] = image.shape[0]
    x[x > image.shape[1]] = image.shape[1]
    centroids[y, x] = np.arange(1, n + 1)

    # Despite masking some objects are detected outside regions of interest.
    # Let's make absolutely that no object lies outside.
    centroids[mask == 0] = 0
    mh.labeled.relabel(centroids, inplace=True)
    blobs[mask == 0] = 0
    mh.labeled.relabel(blobs, inplace=True)
    # TODO: check that labels are the same between centroids and blobs

    ret = collections.namedtuple('blobs', ['centroids', 'blobs'])
    return ret(centroids, blobs)
