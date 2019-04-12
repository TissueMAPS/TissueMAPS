# Copyright (C) 2017-2018 University of Zurich.
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
from jtlib.features import Morphology

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
    if len(primary_sizes) > 1:
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


# All the labeling is done with 8-connectivity (not the default 4 of mahotas)
NEIGHBORHOOD8 = np.ones((3,3), np.bool)

def separate_clumped_objects(clumps_image, min_cut_area, min_area, max_area,
        max_circularity, max_convexity, allow_trimming = True):
    '''Separates objects in `clumps_image` based on morphological criteria.
    
    Parameters
    ----------
    clumps_image: numpy.ndarray[Union[numpy.int32, numpy.bool]]
        objects that should be separated
    min_cut_area: int
        minimal area an object must have (prevents cuts that would result
        in too small objects)
    min_area: int
        minimal area an object must have to be considered a clump
    max_area: int
        maximal area an object can have to be considered a clump
    max_circularity: float
        maximal circularity an object must have to be considerd a clump
    max_convexity: float
        maximal convexity an object must have to be considerd a clump
    allow_trimming: boolean
        Some cuts may create a tiny third object. If this boolean is true,
        tertiary objects < trimming_threshold (10) pixels will be removed
        
    Returns
    -------
    numpy.ndarray[numpy.uint32]
        separated objects
    See also
    --------
    :class:`jtlib.features.Morphology`
    '''

    logger.info('separate clumped objects')
    trimming_threshold = 10

    label_image, n_objects = mh.label(clumps_image, NEIGHBORHOOD8)
    if n_objects == 0:
        logger.debug('no objects')
        return label_image

    pad = 1
    cutting_pass = 1
    separated_image = label_image.copy()
    while True:
        logger.info('cutting pass #%d', cutting_pass)
        cutting_pass += 1
        label_image = mh.label(label_image > 0, NEIGHBORHOOD8)[0]

        f = Morphology(label_image)
        values = f.extract()
        index = (
            (min_area < values['Morphology_Area']) &
            (values['Morphology_Area'] <= max_area) &
            (values['Morphology_Convexity'] <= max_convexity) &
            (values['Morphology_Circularity'] <= max_circularity)
        )
        clumped_ids = values[index].index.values
        not_clumped_ids = values[~index].index.values

        if len(clumped_ids) == 0:
            logger.debug('no more clumped objects')
            break

        mh.labeled.remove_regions(label_image, not_clumped_ids, inplace=True)
        mh.labeled.relabel(label_image, inplace=True)
        bboxes = mh.labeled.bbox(label_image)
        for oid in np.unique(label_image[label_image > 0]):
            bbox = bboxes[oid]
            logger.debug('process clumped object #%d', oid)
            obj_image = extract_bbox(label_image, bboxes[oid], pad=pad)
            obj_image = obj_image == oid

            # Rescale distance intensities to make them independent of clump size
            dist = mh.stretch(mh.distance(obj_image))

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

            # Use the line separating watershed regions to make the cut
            line = mh.labeled.borders(regions, NEIGHBORHOOD8)
            line[~obj_image] = 0

            # Ensure that cut is reasonable given user-defined criteria
            test_cut_image = obj_image.copy()
            test_cut_image[line] = False
            subobjects, n_subobjects = mh.label(test_cut_image, NEIGHBORHOOD8)
            sizes = mh.labeled.labeled_size(subobjects)
            smaller_object_area = np.min(sizes)

            # Deal with an edge-case: If trimming is active & there are more
            # than 2 objects created by the cut, check if they are very small.
            # If so, remove them.
            if allow_trimming and n_subobjects > 2 and smaller_object_area < trimming_threshold:
                tiny_objects = np.nonzero(sizes < trimming_threshold)[0].tolist()
                # Remove objects by adding them to the cutting line
                for trim_obj in tiny_objects:
                    line[subobjects == trim_obj] = True
                    logger.debug('Trimming an object of size: {}'.format(sizes[trim_obj]))

                # Redo calculation if split should be applied
                test_cut_image = obj_image.copy()
                test_cut_image[line] = False
                subobjects, n_subobjects = mh.label(test_cut_image,
                                                    NEIGHBORHOOD8)
                sizes = mh.labeled.labeled_size(subobjects)
                smaller_object_area = np.min(sizes)


            logger.debug('Number of objects: {}'.format(n_subobjects))

            do_cut = (
                (smaller_object_area > min_cut_area) &
                (np.sum(line) > 0)
            )
            if do_cut:
                logger.debug('cut object #%d', oid)
                y, x = np.where(line)
                y_offset, x_offset = bboxes[oid][[0, 2]] - pad
                y += y_offset
                x += x_offset
                label_image[y, x] = 0
                separated_image[y, x] = 0
            else:
                logger.debug('don\'t cut object #%d', oid)
                mh.labeled.remove_regions(label_image, oid, inplace=True)

    return mh.label(separated_image, NEIGHBORHOOD8)[0]
