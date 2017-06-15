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
        n_objects = np.max(primary_label_image)
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
        # We compute the watershed transform using the seeds of the primary
        # objects and the additional seeds for the background regions. The
        # background regions will compete with the foreground regions and
        # thereby work as a stop criterion for expansion of primary objects.
        labels = primary_label_image + background_label_image
        regions = mh.cwatershed(np.invert(intensity_image), labels)
        # Remove background regions
        regions[regions > n_objects] = 0
        # regions[intensity_image < background_level] = 0

        # Ensure objects are separated
        lines = mh.labeled.borders(regions)
        regions[lines] = 0

        # Close holes in objects.
        foreground_mask = regions > 0
        holes = mh.close_holes(foreground_mask) - foreground_mask
        holes = mh.morph.dilate(holes)
        holes_labeled, n_holes = mh.label(holes)
        for i in range(1, n_holes+1):
            fill_value = np.unique(regions[holes_labeled == i])[-1]
            fill_value = fill_value[fill_value > 0][0]
            regions[holes_labeled == i] = fill_value

        # Remove objects that are obviously too small, i.e. smaller than any of
        # the seeds (this could happen when we remove certain parts of objects
        # after the watershed region growing)
        # TODO: Ensure that mapping of objects is one-to-one, i.e. each primary
        # object has exactly one secondary object
        min_size = np.min(mh.labeled.labeled_size(primary_label_image))
        sizes = mh.labeled.labeled_size(regions)
        too_small = np.where(sizes < min_size)
        regions = mh.labeled.remove_regions(regions, too_small)

        # Remove regions that don't overlap with primary objects and assign
        # correct labels, i.e. those of the primary objects.
        logger.info('relabel secondary objects according to primary objects')
        new_label_image, n_new_labels = mh.labeled.relabel(regions)
        lut = np.zeros(np.max(new_label_image)+1, new_label_image.dtype)
        for i in range(1, n_new_labels+1):
            orig_labels = primary_label_image[new_label_image == i]
            orig_labels = orig_labels[orig_labels > 0]
            orig_count = np.bincount(orig_labels)
            orig_unique = np.where(orig_count)[0]
            if orig_unique.size == 1:
                lut[i] = orig_unique[0]
            elif orig_unique.size > 1:
                logger.debug(
                    'overlapping objects: %s',
                    ', '.join(map(str, orig_unique))
                )
                lut[i] = np.where(orig_count == np.max(orig_count))[0][0]
        secondary_label_image = lut[new_label_image]

    # Ensure that primary objects are fully contained within primary objects
    index = (primary_label_image - secondary_label_image) > 0
    secondary_label_image[index] = primary_label_image[index]

    if plot:
        from jtlib import plotting
        n_objects = len(np.unique(secondary_label_image)[1:])
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

