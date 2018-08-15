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
'''Jterator module for segmentation of secondary objects around existing
primary objects.
'''
import logging
import numpy as np
import mahotas as mh
import collections

from jtlib.segmentation import expand_objects_watershed

logger = logging.getLogger(__name__)

VERSION = '0.0.3'

Output = collections.namedtuple('Output', ['secondary_label_image', 'figure'])


def main(primary_label_image, intensity_image, contrast_threshold,
        min_threshold=None, max_threshold=None, plot=False):
    '''Detects secondary objects in an image by expanding the primary objects
    encoded in `primary_label_image`. The outlines of secondary objects are
    determined based on the watershed transform of `intensity_image` using the
    primary objects in `primary_label_image` as seeds.

    Parameters
    ----------
    primary_label_image: numpy.ndarray[numpy.int32]
        2D labeled array encoding primary objects, which serve as seeds for
        watershed transform
    intensity_image: numpy.ndarray[numpy.uint8 or numpy.uint16]
        2D grayscale array that serves as gradient for watershed transform;
        optimally this image is enhanced with a low-pass filter
    contrast_threshold: int
        contrast threshold for automatic separation of forground from background
        based on locally adaptive thresholding (when ``0`` threshold defaults
        to `min_threshold` manual thresholding)
    min_threshold: int, optional
        minimal foreground value; pixels below `min_threshold` are considered
        background
    max_threshold: int, optional
        maximal foreground value; pixels above `max_threshold` are considered
        foreground
    plot: bool, optional
        whether a plot should be generated

    Returns
    -------
    jtmodules.segment_secondary.Output

    Note
    ----
    Setting `min_threshold` and `max_threshold` to the same value reduces
    to manual thresholding.
    '''
    if np.any(primary_label_image == 0):
        has_background = True
    else:
        has_background = False

    if not has_background:
        secondary_label_image = primary_label_image
    else:
        # A simple, fixed threshold doesn't work for SE stains. Therefore, we
        # use adaptive thresholding to determine background regions,
        # i.e. regions in the intensity_image that should not be covered by
        # secondary objects.
        n_objects = len(np.unique(primary_label_image[1:]))
        logger.info(
            'primary label image has %d objects',
            n_objects - 1
        )
        # SB: Added a catch for images with no primary objects
        # note that background is an 'object'
        if n_objects > 1:
            # TODO: consider using contrast_treshold as input parameter
            background_mask = mh.thresholding.bernsen(
                intensity_image, 5, contrast_threshold
            )
            if min_threshold is not None:
                logger.info(
                    'set lower threshold level to %d', min_threshold
                )
                background_mask[intensity_image < min_threshold] = True

            if max_threshold is not None:
                logger.info(
                    'set upper threshold level to %d', max_threshold
                )
                background_mask[intensity_image > max_threshold] = False
            # background_mask = mh.morph.open(background_mask)
            background_label_image = mh.label(background_mask)[0]
            background_label_image[background_mask] += n_objects

            logger.info('detect secondary objects via watershed transform')
            secondary_label_image = expand_objects_watershed(
                primary_label_image, background_label_image, intensity_image
            )
        else:
            logger.info('skipping secondary segmentation')
            secondary_label_image = np.zeros(
                primary_label_image.shape, dtype=np.int32
            )

    n_objects = len(np.unique(secondary_label_image)[1:])
    logger.info('identified %d objects', n_objects)

    if plot:
        from jtlib import plotting
        colorscale = plotting.create_colorscale(
            'Spectral', n=n_objects, permute=True, add_background=True
        )
        outlines = mh.morph.dilate(mh.labeled.bwperim(secondary_label_image > 0))
        plots = [
            plotting.create_mask_image_plot(
                primary_label_image, 'ul', colorscale=colorscale
                ),
            plotting.create_mask_image_plot(
                secondary_label_image, 'ur', colorscale=colorscale
            ),
            plotting.create_intensity_overlay_image_plot(
                intensity_image, outlines, 'll'
            )
        ]
        figure = plotting.create_figure(plots, title='secondary objects')
    else:
        figure = str()

    return Output(secondary_label_image, figure)

