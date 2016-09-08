'''Jterator module for separation of clumps in a binary image,
where a `clump` is a connected component with certain size and shape.
'''
import numpy as np
import cv2
import mahotas as mh
import skimage.morphology
import logging
import jtlib.utils

VERSION = '0.0.4'

logger = logging.getLogger(__name__)
PAD = 1


def find_concave_regions(mask, max_dist):
    '''Finds convace regions along the contour of `mask`.

    Parameters
    ----------
    mask: numpy.ndarray[numpy.bool]
        mask image
    max_dist: int
        maximally tolerated distance between concave point on object contour
        and the convex hull
    Note
    ----
    Fast implementation in C++ using `OpenCV library <http://opencv.org/>`_.
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


def find_watershed_lines(mask, img, ksize):
    '''Finds watershed lines in the region of `img` defined by `mask`.
    The seeds for the watershed are automatically determined using thresholding
    (Otsu's method). The thereby created mask is morphologically opened using
    a squared structuring element of size `ksize`.

    Parameters
    ----------
    mask: numpy.ndarray[numpy.bool]
        mask image
    img: numpy.ndarray[numpy.uint8 or numpy.uint16]
        intensity image
    ksize: int
        size of the kernel that's used to detect regional maxima in `img`
        within `mask`

    Returns
    -------
    numpy.ndarray[numpy.bool]
        image with lines that separate neighbouring watershed regions

    Note
    ----
    Fast implementation in C++ using
    `mahotas library <http://mahotas.readthedocs.io/en/latest/>`_.
    '''

    if ksize < 2:
        ksize = 2
    se = skimage.morphology.square(ksize)
    peaks = mh.morph.regmax(img, Bc=se)
    seeds = mh.label(peaks)[0]
    watershed_regions = mh.cwatershed(np.invert(img), seeds)
    watershed_regions[~mask] = 0
    lines = mh.labeled.borders(watershed_regions)
    outer_lines = mh.labeled.borders(mask)
    lines[outer_lines] = 0
    lines = mh.thin(lines)
    labeled_lines = mh.label(lines)[0]
    sizes = mh.labeled.labeled_size(labeled_lines)
    too_small = np.where(sizes < 10)
    lines = mh.labeled.remove_regions(labeled_lines, too_small) > 0
    return lines


def find_nodes_closest_to_concave_regions(concave_region_points, end_points, nodes):
    '''Finds end points within shortest distance to each concave region.

    Parameters
    ----------
    concave_region_points: numpy.ndarray[numpy.int32]
        labeled points marking concave regions on the object contour
    end_points: numpy.ndarray[numpy.int32]
        labeled points marking intersection points between lines and the
        object contour
    nodes: numpy.ndarray[numpy.int32]
        all labeled points

    Returns
    -------
    Dict[int, int]
        mapping of concave region points to closest end points
    '''
    concave_region_point_node_map = dict()
    concave_region_point_ids = np.unique(concave_region_points)[1:]
    end_point_ids = np.unique(end_points)[1:]
    for cid in concave_region_point_ids:
        cpt = np.array(np.where(concave_region_points == cid)).T[0, :]
        dists = dict()
        for eid in end_point_ids:
            ept = np.array(np.where(end_points == eid)).T[0, :]
            # We use end point id to retrieve the correct coordinate,
            # we want to track the point by node id
            nid = nodes[tuple(ept)]
            dists[nid] = np.linalg.norm(cpt - ept)
        if not dists:
            return dict()
        min_dist = np.min(dists.values())
        concave_region_point_node_map.update({
            cid: nid for nid, d in dists.iteritems() if d == min_dist
        })
    return concave_region_point_node_map


def calc_area_shape_features(mask):
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


# def calc_complex_shape_features(mask):
#     '''Calculates Zernike moments that describe the shape of the object
#     in mask.

#     Parameters
#     ----------
#     mask: numpy.ndarray[numpy.bool]
#         bounding box image containing the object where ``True`` is foreground
#         and ``False`` background

#     Returns
#     -------
#     numpy.ndarray[numpy.float64]
#         shape features
#     '''
#     radius = 100
#     mask_rs = mh.imresize(mask, (radius, radius))
#     return mh.features.zernike_moments(mask, degree= 12, radius=radius/2)


def create_area_shape_feature_images(label_image):
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
        shape_features = calc_area_shape_features(mask)
        for j, f in enumerate(shape_features):
            images[j][label_image == i] = f
    return tuple(images)


def main(input_mask, input_image, min_area, max_area,
        min_cut_area, max_form_factor, max_solidity, cutting_passes,
        plot=False):
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

    Returns
    -------
    Dict[str, numpy.ndarray[numpy.bool] or str]
        * "output_mask": image with cut clumped objects
        * "figure": JSON figure representation
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

            area, form_factor, solidity = calc_area_shape_features(mask)
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
                    tmp = mh.morph.erode(peaks)
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
            area, form_factor, solidity = calc_area_shape_features(smaller_object)

            # TODO: We may want to prevent cuts that go through areas with
            # high distance intensity values
            if area < min_cut_area:
                logger.warn(
                    'object %d not cut - resulting object too small', oid
                )
                continue

            # Update cut mask
            logger.info('cut object %d', oid)
            y, x = np.where(mh.morph.dilate(line))
            y_offset, x_offset = bboxes[oid][[0, 2]] - PAD
            y += y_offset
            x += x_offset
            cut_mask[y, x] = True

        output_mask[cut_mask] = 0

    output = dict()
    output['output_mask'] = output_mask
    if plot:
        from jtlib import plotting
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
        output['figure'] = plotting.create_figure(
            plots, title='separated clumps'
        )
    else:
        output['figure'] = str()

    return output
