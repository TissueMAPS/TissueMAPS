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
import cv2
import numpy as np
import mahotas as mh
import sep

from jtlib.utils import extract_bbox

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


def expand_objects_watershed(seeds_image, background_image, intensity_image):
    '''Expands objects in `seeds_image` using a watershed transform
    on `intensity_image`.

    Parameters
    ----------
    seeds_image: numpy.ndarray[numpy.int32]
        objects that should be expanded
    background_image: numpy.ndarray[numpy.bool]
        regions in the image that should be considered background and should
        not be part of an object after expansion
    intensity_image: numpy.ndarray[Union[numpy.uint8, numpy.uint16]]
        grayscale image; pixel intensities determine how far individual
        objects are expanded

    Returns
    -------
    numpy.ndarray[numpy.int32]
        expanded objects
    '''
    # We compute the watershed transform using the seeds of the primary
    # objects and the additional seeds for the background regions. The
    # background regions will compete with the foreground regions and
    # thereby work as a stop criterion for expansion of primary objects.
    logger.info('apply watershed transform to expand objects')
    labels = seeds_image + background_image
    regions = mh.cwatershed(np.invert(intensity_image), labels)
    # Remove background regions
    n_objects = len(np.unique(seeds_image[seeds_image > 0]))
    regions[regions > n_objects] = 0

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
    primary_sizes = mh.labeled.labeled_size(seeds_image)
    min_size = np.min(primary_sizes[1:]) + 1
    regions = mh.labeled.filter_labeled(regions, min_size=min_size)[0]

    # Remove regions that don't overlap with seed objects and assign
    # correct labels to the other regions, i.e. those of the corresponding seeds.
    logger.debug('relabel expanded objects according to their seeds')
    new_label_image, n_new_labels = mh.labeled.relabel(regions)
    lut = np.zeros(np.max(new_label_image)+1, new_label_image.dtype)
    for i in range(1, n_new_labels+1):
        orig_labels = seeds_image[new_label_image == i]
        orig_labels = orig_labels[orig_labels > 0]
        orig_count = np.bincount(orig_labels)
        orig_unique = np.where(orig_count)[0]
        if orig_unique.size == 1:
            lut[i] = orig_unique[0]
        elif orig_unique.size > 1:
            logger.warn(
                'objects overlap after expansion: %s',
                ', '.join(map(str, orig_unique))
            )
            lut[i] = np.where(orig_count == np.max(orig_count))[0][0]
    expanded_image = lut[new_label_image]

    # Ensure that seed objects are fully contained within expanded objects
    index = (seeds_image - expanded_image) > 0
    expanded_image[index] = seeds_image[index]

    return expanded_image


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


def _calc_morphology(mask):
    '''Calcuates *area*, *circularity* and *convexity* for a given object.

    Parameters
    ----------
    mask: numpy.ndarray[numpy.bool]
        bounding box image representing the object as a continuous region of
        positive pixels

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


def separate_clumped_objects(clumps_image, min_cut_area, min_area, max_area,
        max_circularity, max_convexity):
    '''Separates objects in `clumps_image` based on morphological criteria.

    Parameters
    ----------
    clumps_image: numpy.ndarray[Union[numpy.int32, numpy.bool]]
        objects that should be separated
    min_cut_area: int
        minimal area a cut object can have
    min_area: int
        minimal area an object must have to be considered a clump
    max_area: int
        maximal area an object can have to be considered a clump
    max_circularity: float
        maximal circularity an object must have to be considerd a clump
    max_convexity: float
        maximal convexity an object must have to be considerd a clump

    Returns
    -------
    numpy.ndarray[numpy.uint32]
        separated objects
    '''
    PAD = 1
    separated_image = clumps_image.copy()
    cut_mask = np.zeros(separated_image.shape, bool)

    label_image = mh.label(clumps_image > 0)[0]
    object_ids = np.unique(label_image[label_image > 0])
    if len(object_ids) == 0:
        logger.debug('no objects')
        return separated_image

    bboxes = mh.labeled.bbox(label_image)
    for oid in object_ids:
        logger.debug('process object #%d', oid)
        obj_clumps_image = extract_bbox(label_image, bboxes[oid], pad=1)
        obj_clumps_image = obj_clumps_image == oid

        area, circularity, convexity = _calc_morphology(obj_clumps_image)
        if area < min_area or area > max_area:
            logger.debug('not a clump - outside area range')
            continue
        if circularity > max_circularity:
            logger.debug('not a clump - above form factor threshold')
            continue
        if convexity > max_convexity:
            logger.debug('not a clump - above convexity threshold')
            continue

        y, x = np.where(obj_clumps_image)
        y_offset, x_offset = bboxes[oid][[0, 2]] - PAD - 1
        y += y_offset
        x += x_offset

        # Rescale distance intensities to make them independent of clump size
        dist = mh.stretch(mh.distance(obj_clumps_image))

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
        line[~obj_clumps_image] = 0
        line = mh.morph.dilate(line)

        # Ensure that cut is reasonable given user-defined criteria
        test_cut_clumps_image = obj_clumps_image.copy()
        test_cut_clumps_image[line] = False
        test_cut_clumps_image = mh.morph.open(test_cut_clumps_image)
        subobjects, n_subobjects = mh.label(test_cut_clumps_image)
        sizes = mh.labeled.labeled_size(subobjects)
        smaller_id = np.where(sizes == np.min(sizes))[0][0]
        smaller_object = subobjects == smaller_id
        area, circularity, convexity = _calc_morphology(smaller_object)

        # TODO: We may want to prevent cuts that go through areas with
        # high distance intensity values.
        if area < min_cut_area:
            logger.debug(
                'object %d not cut - resulting object too small', oid
            )
            continue

        # Update cut clumps_image
        logger.debug('cut object %d', oid)
        y, x = np.where(line)
        y_offset, x_offset = bboxes[oid][[0, 2]] - PAD - 1
        y += y_offset
        x += x_offset
        cut_mask[y, x] = True

        separated_image[cut_mask] = False

        return separated_image
