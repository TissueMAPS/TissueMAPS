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
'''Jterator module for separation of clumps in a binary image,
where a `clump` is defined as a connected component of certain size and shape.
'''
import numpy as np
import cv2
import mahotas as mh
import skimage.morphology
import logging
import collections
import jtlib.utils
from jtlib.features import Morphology, create_feature_image

VERSION = '0.1.1'

logger = logging.getLogger(__name__)
PAD = 1

Output = collections.namedtuple('Output', ['separated_mask', 'figure'])


def find_concave_regions(mask, max_dist):
    '''Finds convace regions along the contour of `mask`.

    Parameters
    ----------
    mask: numpy.ndarray[numpy.bool]
        mask image
    max_dist: int
        maximally tolerated distance between concave point on object contour
        and the convex hull
    '''
    contour_img = np.zeros(mask.shape, dtype=np.uint8)
    contour_img[mask] = 255
    contour_img, contours, _ = cv2.findContours(
        contour_img, mode=cv2.RETR_EXTERNAL, method=cv2.CHAIN_APPROX_SIMPLE
    )
    concave_img = np.zeros(mask.shape, dtype=np.bool)
    for cnt in contours:
        hull = cv2.convexHull(cnt, returnPoints=False)
        defects = cv2.convexityDefects(cnt, hull)
        if defects is not None:
            defect_pts = np.array([
                cnt[defects[j, 0][2]][0]
                for j in xrange(defects.shape[0])
                if defects[j, 0][3]/float(256) > max_dist
            ])
            if defect_pts.size != 0:
                concave_img[defect_pts[:, 1], defect_pts[:, 0]] = True
    return mh.label(concave_img)


def _calc_features(mask):
    '''Calcuates *area*, *circularity* and *convexity* for the given object.

    Parameters
    ----------
    mask: numpy.ndarray[numpy.bool]
        bounding box image representing the object

    Returns
    -------
    Tuple[numpy.float64]
        area, circularity and convexity
    '''
    mask = mask > 0
    area = np.float64(np.count_nonzero(mask))
    perimeter = mh.labeled.perimeter(mask)
    if perimeter == 0:
        circularity = np.nan
    else:
        circularity = (4.0 * np.pi * area) / (perimeter**2)
    convex_hull = mh.polygon.fill_convexhull(mask)
    area_convex_hull = np.count_nonzero(convex_hull)
    convexity = area / area_convex_hull
    # eccentricity = mh.features.eccentricity(mask)
    # roundness = mh.features.roundness(mask)
    # major_axis, minor_axis = mh.features.ellipse_axes(mask)
    # elongation = (major_axis - minor_axis) / major_axis
    return (area, circularity, convexity)


def main(mask, intensity_image, min_area, max_area,
        min_cut_area, max_circularity, max_convexity, cutting_passes,
        plot=False, selection_test_mode=False):
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
        maximal area an object must have to be considered a clump
    min_cut_area: int
        minimal area a cut object can have
        (useful to limit size of cut objects)
    max_convexity: float
        maximal convexity an object must have to be considerd a clump
    max_circularity: float
        maximal form factor an object must have to be considerd a clump
    cutting_passes: int
        number of cutting cycles to separate clumps that consist of more than
        two subobjects
    plot: bool, optional
        whether a plot should be generated
    selection_test_mode: bool, optional
        whether, instead of the normal plot, heatmaps should be generated that
        display values of the selection criteria *area*, *circularity* and
        *convexity* for each individual object in `mask` as well as
        the selected "clumps" based on the criteria provided by the user

    Returns
    -------
    jtmodules.separate_clumps.Output
    '''
    mask = mask > 0
    separated_mask = mask.copy()
    cut_mask = np.zeros(separated_mask.shape, bool)
    clumps_mask = np.zeros(separated_mask.shape, bool)
    for n in range(cutting_passes):
        logger.info('cutting pass #%d', n+1)
        label_image = mh.label(separated_mask)[0]
        object_ids = np.unique(label_image[label_image > 0])
        if len(object_ids) == 0:
            logger.debug('no objects')
            continue

        bboxes = mh.labeled.bbox(label_image)
        for oid in object_ids:
            logger.debug('process object #%d', oid)
            obj_mask = jtlib.utils.extract_bbox(
                label_image, bboxes[oid], pad=PAD
            )
            obj_mask = obj_mask == oid
            int_img = jtlib.utils.extract_bbox(
                intensity_image, bboxes[oid], pad=PAD
            )

            area, circularity, convexity = _calc_features(obj_mask)
            if area < min_area or area > max_area:
                logger.debug('not a clump - outside area range')
                continue
            if circularity > max_circularity:
                logger.debug('not a clump - above form factor threshold')
                continue
            if convexity > max_convexity:
                logger.debug('not a clump - above convexity threshold')
                continue

            y, x = np.where(obj_mask)
            y_offset, x_offset = bboxes[oid][[0, 2]] - PAD - 1
            y += y_offset
            x += x_offset
            clumps_mask[y, x] = True

            # Rescale distance intensities to make them independent of clump size
            dist = mh.stretch(mh.distance(obj_mask))

            # Find peaks that can be used as seeds for the watershed transform
            thresh = mh.otsu(dist)
            peaks = dist > thresh
            n = mh.label(peaks)[1]
            if n == 1:
                logger.debug(
                    'only one peak detected - perform iterative erosion'
                )
                # Iteratively shrink the peaks until we have two peaks that we
                # can use to separate the clump.
                while True:
                    tmp = mh.morph.open(mh.morph.erode(peaks))
                    n = mh.label(tmp)[1]
                    if n == 2 or n == 0:
                        if n == 2:
                            peaks = tmp
                        break
                    peaks = tmp

            # Select the two biggest peaks, since we want only two objects.
            peaks = mh.label(peaks)[0]
            sizes = mh.labeled.labeled_size(peaks)
            index = np.argsort(sizes)[::-1][1:3]
            for label in np.unique(peaks):
                if label not in index:
                    peaks[peaks == label] = 0
            peaks = mh.labeled.relabel(peaks)[0]
            regions = mh.cwatershed(np.invert(dist), peaks)

            # Use the line separating the watershed regions to make the cut
            se = np.ones((3,3), np.bool)
            line = mh.labeled.borders(regions, Bc=se)
            line[~obj_mask] = 0
            line = mh.morph.dilate(line)

            # Ensure that cut is reasonable given user-defined criteria
            test_cut_mask = obj_mask.copy()
            test_cut_mask[line] = False
            test_cut_mask = mh.morph.open(test_cut_mask)
            subobjects, n_subobjects = mh.label(test_cut_mask)
            sizes = mh.labeled.labeled_size(subobjects)
            smaller_id = np.where(sizes == np.min(sizes))[0][0]
            smaller_object = subobjects == smaller_id
            area, circularity, convexity = _calc_features(smaller_object)

            # TODO: We may want to prevent cuts that go through areas with
            # high distance intensity values.
            if area < min_cut_area:
                logger.debug(
                    'object %d not cut - resulting object too small', oid
                )
                continue

            # Update cut mask
            logger.debug('cut object %d', oid)
            y, x = np.where(line)
            y_offset, x_offset = bboxes[oid][[0, 2]] - PAD - 1
            y += y_offset
            x += x_offset
            cut_mask[y, x] = True

        separated_mask[cut_mask] = False

    if plot:
        from jtlib import plotting
        if selection_test_mode:
            logger.info('create plot for selection test mode')
            labeled_mask, n_objects = mh.label(mask, np.ones((3, 3), bool))
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
            area_colorscale = plotting.create_colorscale(
                'Greens', n_objects,
                add_background=True, background_color='white'
            )
            circularity_colorscale = plotting.create_colorscale(
                'Blues', n_objects,
                add_background=True, background_color='white'
            )
            convexity_colorscale = plotting.create_colorscale(
                'Reds', n_objects,
                add_background=True, background_color='white'
            )
            plots = [
                plotting.create_float_image_plot(
                    area_img, 'ul', colorscale=area_colorscale
                ),
                plotting.create_float_image_plot(
                    convexity_img, 'ur', colorscale=convexity_colorscale
                ),
                plotting.create_float_image_plot(
                    circularity_img, 'll', colorscale=circularity_colorscale
                ),
                plotting.create_mask_image_plot(
                    clumps_mask, 'lr'
                ),
            ]
            figure = plotting.create_figure(
                plots,
                title=(
                    'Selection criteria: "area" (green), "convexity" (red) '
                    'and "circularity" (blue)'
                )
            )
        else:
            logger.info('create plot')
            labeled_separated_mask, n_objects = mh.label(
                separated_mask, np.ones((3, 3), bool)
            )
            colorscale = plotting.create_colorscale(
                'Spectral', n=n_objects, permute=True, add_background=True
            )
            outlines = mh.morph.dilate(mh.labeled.bwperim(separated_mask))
            cutlines = mh.morph.dilate(mh.labeled.bwperim(cut_mask))
            plots = [
                plotting.create_mask_image_plot(
                    labeled_separated_mask, 'ul', colorscale=colorscale
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
