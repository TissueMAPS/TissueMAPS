# Copyright (C) 2016-2018 University of Zurich.
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
'''Jterator module for separation of clumps in a binary image,
where a `clump` is defined as a connected component of certain size and shape.
'''
import numpy as np
import cv2
import mahotas as mh
import skimage.morphology
import logging
import collections

from jtlib.segmentation import separate_clumped_objects
from jtlib.features import Morphology, create_feature_image

VERSION = '0.2.2'

logger = logging.getLogger(__name__)

Output = collections.namedtuple('Output', ['separated_mask', 'figure'])



def main(mask, intensity_image, min_area, max_area,
        min_cut_area, max_circularity, max_convexity,
        plot=False, selection_test_mode=False,
        selection_test_show_remaining=False):
    '''Detects clumps in `mask` given criteria provided by the user
    and cuts them along the borders of watershed regions, which are determined
    based on the distance transform of `mask`.

    Parameters
    ----------
    mask: numpy.ndarray[Union[numpy.int32, numpy.bool]]
        2D binary or labele image encoding potential clumps
    intensity_image: numpy.ndarray[numpy.uint8 or numpy.uint16]
        2D grayscale image with intensity values of the objects that should
        be detected
    min_area: int
        minimal area an object must have to be considered a clump
    max_area: int
        maximal area an object can have to be considered a clump
    min_cut_area: int
        minimal area an object must have
        (useful to prevent cuts that would result in too small objects)
    max_circularity: float
        maximal circularity an object can have to be considerd a clump
    max_convexity: float
        maximal convexity an object can have to be considerd a clump
    plot: bool, optional
        whether a plot should be generated
    selection_test_mode: bool, optional
        whether, instead of the normal plot, heatmaps should be generated that
        display values of the selection criteria *area*, *circularity* and
        *convexity* for each individual object in `mask` as well as
        the selected "clumps" based on the criteria provided by the user
    selection_test_show_remaining: bool, optional
        whether the selection test plot should be made on the remaining image
        after the cuts were performed (helps to see why some objects were not
        cut, especially if there are complicated clumps that require multiple
        cuts). Defaults to false, thus showing the values in the original image

    Returns
    -------
    jtmodules.separate_clumps.Output
    '''

    separated_mask = separate_clumped_objects(
        mask, min_cut_area, min_area, max_area,
        max_circularity, max_convexity
    )

    if plot:
        from jtlib import plotting

        clumps_mask = np.zeros(mask.shape, bool)
        initial_objects_label_image, n_initial_objects = mh.label(mask > 0)
        for n in range(1, n_initial_objects+1):
            obj = (initial_objects_label_image == n)
            if len(np.unique(separated_mask[obj])) > 1:
                clumps_mask[obj] = True

        cut_mask = (mask > 0) & (separated_mask == 0)
        cutlines = mh.morph.dilate(mh.labeled.bwperim(cut_mask))

        if selection_test_mode:
            logger.info('create plot for selection test mode')

            # Check if selection_test_show_remaining is active
            # If so, show values on processed image, not original
            if selection_test_show_remaining:
                labeled_mask, n_objects = mh.label(separated_mask > 0)
                logger.info('Selection test mode plot with processed image')
            else:
                labeled_mask, n_objects = mh.label(mask)
            f = Morphology(labeled_mask)
            values = f.extract()
            area_img = create_feature_image(
                values['Morphology_Area'].values, labeled_mask
            )
            convexity_img = create_feature_image(
                values['Morphology_Convexity'].values, labeled_mask
            )
            circularity_img = create_feature_image(
                values['Morphology_Circularity'].values, labeled_mask
            )
            plots = [
                plotting.create_float_image_plot(
                    area_img, 'ul'
                ),
                plotting.create_float_image_plot(
                    convexity_img, 'ur'
                ),
                plotting.create_float_image_plot(
                    circularity_img, 'll'
                ),
                plotting.create_mask_overlay_image_plot(
                    clumps_mask, cutlines, 'lr'
                ),
            ]
            figure = plotting.create_figure(
                plots,
                title=(
                    'Selection criteria:'
                    ' "area" (top left),'
                    ' "convexity" (top-right),'
                    ' and "circularity" (bottom-left);'
                    ' cuts made (bottom right).'
                )
            )
        else:
            logger.info('create plot')

            n_objects = len(np.unique(separated_mask[separated_mask > 0]))
            colorscale = plotting.create_colorscale(
                'Spectral', n=n_objects, permute=True, add_background=True
            )
            outlines = mh.morph.dilate(mh.labeled.bwperim(separated_mask > 0))
            plots = [
                plotting.create_mask_image_plot(
                    separated_mask, 'ul', colorscale=colorscale
                ),
                plotting.create_intensity_overlay_image_plot(
                    intensity_image, outlines, 'ur'
                ),
                plotting.create_mask_overlay_image_plot(
                    clumps_mask, cutlines, 'll'
                )
            ]
            figure = plotting.create_figure(
                plots, title='separated clumps'
            )
    else:
        figure = str()

    return Output(separated_mask, figure)
