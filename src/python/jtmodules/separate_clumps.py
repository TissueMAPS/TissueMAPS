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

VERSION = '0.0.5'

logger = logging.getLogger(__name__)
PAD = 1

Output = collections.namedtuple('Output', ['output_mask', 'figure'])


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


def calc_features(mask):
    '''Calcuates `area` and shape features `form factor` and `solidity`
    for the given object.

    Parameters
    ----------
    mask: numpy.ndarray[numpy.bool]
        bounding box image representing the object

    Returns
    -------
    numpy.ndarray[numpy.float64]
        area, form factor and solidity
    '''
    mask = mask > 0
    area = np.float64(np.count_nonzero(mask))
    perimeter = mh.labeled.perimeter(mask)
    form_factor = (4.0 * np.pi * area) / (perimeter**2)
    convex_hull = mh.polygon.fill_convexhull(mask)
    area_convex_hull = np.count_nonzero(convex_hull)
    solidity = area / area_convex_hull
    # eccentricity = mh.features.eccentricity(mask)
    # roundness = mh.features.roundness(mask)
    # major_axis, minor_axis = mh.features.ellipse_axes(mask)
    # elongation = (major_axis - minor_axis) / major_axis
    return np.array([area, form_factor, solidity])


def create_feature_images(label_image):
    '''Creates label images, where each object is color coded according to
    area/shape features.

    Parameters
    ----------
    label_image: numpy.ndarray[numpy.int32]
        labeled image

    Returns
    -------
    Tuple[numpy.ndarray[numpy.float64]]
        heatmap images for each feature
    '''
    label_image = mh.label(label_image > 0)[0]
    bboxes = mh.labeled.bbox(label_image)
    object_ids = np.unique(label_image)[1:]
    images = [np.zeros(label_image.shape, np.float64) for x in range(3)]
    # TODO: might be faster by mapping the image through a lookup table
    for i in object_ids:
        mask = jtlib.utils.extract_bbox_image(label_image, bboxes[i], pad=PAD)
        mask = mask == i
        shape_features = calc_features(mask)
        for j, f in enumerate(shape_features):
            images[j][label_image == i] = f
    return tuple(images)


def main(input_mask, input_image, min_area, max_area,
        min_cut_area, max_form_factor, max_solidity, cutting_passes,
        plot=False, selection_test_mode=False):
    '''Detects clumps in `input_mask` given criteria provided by the user
    and cuts them along the borders of watershed regions, which are determined
    based on the distance transform of `input_mask`.

    Parameters
    ----------
    input_mask: numpy.ndarray[numpy.bool]
        2D binary array encoding potential clumps
    input_image: numpy.ndarray[numpy.uint8 or numpy.uint16]
        2D grayscale array with intensity values of the objects that should
        be detected
    min_area: int
        minimal area an object must have to be considered a clump
    max_area: int
        maximal area an object must have to be considered a clump
    min_cut_area: int
        minimal area a cut object can have
        (useful to limit size of cut objects)
    max_solidity: float
        maximal solidity an object must have to be considerd a clump
    max_form_factor: float
        maximal form factor an object must have to be considerd a clump
    cutting_passes: int
        number of cutting cycles to separate clumps that consist of more than
        two subobjects
    plot: bool, optional
        whether a plot should be generated
    selection_test_mode: bool, optional
        whether, instead the normal plot, heatmaps should be generated that
        display values of the selection criteria *area*, *form factor* and
        *solidity* for each individual object in `input_mask` as well as
        the final selection of "clumps" based on the selection
        criteria provided by the user

    Returns
    -------
    jtmodules.separate_clumps.Output
    '''

    output_mask = input_mask.copy()
    cut_mask = np.zeros(output_mask.shape, bool)
    clumps_mask = np.zeros(output_mask.shape, bool)
    for n in range(cutting_passes):
        logger.info('cutting pass #%d', n+1)
        label_image = mh.label(output_mask)[0]
        object_ids = np.unique(label_image[label_image > 0])
        if len(object_ids) == 0:
            logger.debug('no objects')
            continue

        bboxes = mh.labeled.bbox(label_image)
        for oid in object_ids:
            logger.debug('process object #%d', oid)
            mask = jtlib.utils.extract_bbox_image(
                label_image, bboxes[oid], pad=PAD
            )
            mask = mask == oid

            area, form_factor, solidity = calc_features(mask)
            if area < min_area or area > max_area:
                logger.debug('not a clump - outside area range')
                continue
            if form_factor > max_form_factor:
                logger.debug('not a clump - above form factor threshold')
                continue
            if solidity > max_solidity:
                logger.debug('not a clump - above solidity threshold')
                continue

            y, x = np.where(mask)
            y_offset, x_offset = bboxes[oid][[0, 2]] - PAD
            y += y_offset
            x += x_offset
            clumps_mask[y, x] = True

            # Rescale distance intensities to make them independent of clump size
            dist = mh.stretch(mh.distance(mask))
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

            # Select the two biggest peaks, since want to have only two objects.
            peaks = mh.label(peaks)[0]
            sizes = mh.labeled.labeled_size(peaks)
            index = np.argsort(sizes)[::-1][1:3]
            for label in np.unique(peaks):
                if label not in index:
                    peaks[peaks == label] = 0
            peaks = mh.labeled.relabel(peaks)[0]
            regions = mh.cwatershed(np.invert(dist), peaks)
            regions[~mask] = 0

            # Use the line separating the watershed regions to make the cut
            line = mh.labeled.borders(regions)
            outer_lines = mh.labeled.borders(mask)
            line[outer_lines] = 0

            # Ensure that cut is reasonable give the user defined criteria
            test_cut_mask = mask.copy()
            test_cut_mask[line] = False
            test_cut_mask = mh.morph.open(test_cut_mask)
            subobjects, n_subobjects = mh.label(test_cut_mask)
            sizes = mh.labeled.labeled_size(subobjects)
            smaller_id = np.where(sizes == np.min(sizes))[0][0]
            smaller_object = subobjects == smaller_id
            area, form_factor, solidity = calc_features(smaller_object)

            # TODO: We may want to prevent cuts that go through areas with
            # high distance intensity values
            if area < min_cut_area:
                logger.debug(
                    'object %d not cut - resulting object too small', oid
                )
                continue

            # Update cut mask
            logger.debug('cut object %d', oid)
            y, x = np.where(mh.morph.dilate(line))
            y_offset, x_offset = bboxes[oid][[0, 2]] - PAD
            y += y_offset
            x += x_offset
            cut_mask[y, x] = True

        output_mask[cut_mask] = 0

    if plot:
        from jtlib import plotting
        if selection_test_mode:
            logger.info('create plot for selection test mode')
            labeled_output_mask, n_objects = mh.label(
                input_mask, np.ones((3, 3), bool)
            )
            area_img, form_factor_img, solidity_img = create_feature_images(
                input_mask
            )
            area_colorscale = plotting.create_colorscale(
                'Greens', n_objects,
                add_background=True, background_color='white'
            )
            form_factor_colorscale = plotting.create_colorscale(
                'Blues', n_objects,
                add_background=True, background_color='white'
            )
            solidity_colorscale = plotting.create_colorscale(
                'Reds', n_objects,
                add_background=True, background_color='white'
            )
            plots = [
                plotting.create_float_image_plot(
                    area_img, 'ul', colorscale=area_colorscale
                ),
                plotting.create_float_image_plot(
                    solidity_img, 'ur', colorscale=solidity_colorscale
                ),
                plotting.create_float_image_plot(
                    form_factor_img, 'll', colorscale=form_factor_colorscale
                ),
                plotting.create_mask_image_plot(
                    clumps_mask, 'lr'
                ),
            ]
            figure = plotting.create_figure(
                plots, title='selection test mode'
            )
        else:
            logger.info('create plot')
            labeled_output_mask, n_objects = mh.label(
                output_mask, np.ones((3, 3), bool)
            )
            colorscale = plotting.create_colorscale(
                'Spectral', n=n_objects, permute=True, add_background=True
            )
            outlines = mh.morph.dilate(mh.labeled.bwperim(output_mask))
            cutlines = mh.morph.dilate(mh.labeled.bwperim(cut_mask))
            plots = [
                plotting.create_mask_image_plot(
                    labeled_output_mask, 'ul', colorscale=colorscale
                ),
                plotting.create_intensity_overlay_image_plot(
                    input_image, outlines, 'ur'
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

    return Output(output_mask, figure)
