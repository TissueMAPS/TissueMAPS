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

VERSION = '0.1.0'

logger = logging.getLogger(__name__)

sep.set_extract_pixstack(10**6)

Output = collections.namedtuple('Output', ['mask', 'label_image', 'figure'])


def main(image, threshold_factor=5, min_area=None, max_area=None, plot=False):
    '''Detects blobs in `image` using a Python implementation of
    `SExtractor <http://www.astromatic.net/software/sextractor>`_ [1].

    Parameters
    ----------
    image: numpy.ndarray[numpy.uint8 or numpy.uint16]
        grayscale image in which blobs should be detected
    threshold_factor: int, optional
        factor by which pixel values must be above background RMS noise
        to be considered part of a blob (default: ``5``)
    min_area: int, optional
        minimal size blobs must have (default: ``None``)
    max_area: int, optional
        maximal size blobs can have (default: ``None``)
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    jtmodules.detect_blobs.Output[Union[numpy.ndarray, str]]

    References
    ----------
    _[1] Bertin, E. & Arnouts, S. 1996: SExtractor: Software for source extraction, Astronomy & Astrophysics Supplement 317, 393
    '''

    img = image.astype('float')

    logger.info('estimate background')
    bkg = sep.Background(img)

    logger.info('subtract background')
    img_sub = img - bkg

    logger.info('detect blobs')
    out, blobs_img = sep.extract(
        img_sub, threshold_factor, err=bkg.globalrms,
        segmentation_map=True
    )

    sizes = mh.labeled.labeled_size(blobs_img)
    if min_area is None:
        min_area = np.min(sizes[1:])
    if max_area is None:
        max_area = np.max(sizes[1:])
    filter_criteria = np.logical_or(sizes < min_area, sizes > max_area)
    blobs_img = mh.labeled.remove_regions(blobs_img, np.where(filter_criteria))

    centroids_img = np.zeros(img.shape, dtype=bool)
    y = out['y'][~filter_criteria[1:]].astype(int)
    x = out['x'][~filter_criteria[1:]].astype(int)
    centroids_img[y, x] = True

    if plot:
        logger.info('create plot')
        from jtlib import plotting
        n_objects = len(np.unique(blobs[1:]))
        colorscale = plotting.create_colorscale(
            'Spectral', n=n_objects, permute=True, add_background=True
        )
        plots = [
            plotting.create_intensity_image_plot(
                image, 'ul', clip=True
            ),
            plotting.create_mask_image_plot(
                blobs_img, 'ur', colorscale=colorscale
            )
        ]
        figure = plotting.create_figure(
            plots, title='detected #%d blobs' % n_objects
        )
    else:
        figure = str()

    return Output(centroids_img, blobs_img, figure)
