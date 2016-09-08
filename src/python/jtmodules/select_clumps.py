'''Jterator module for selection of clumped objects in a binary image
based on area/shape criteria given by the user.
'''
import numpy as np
import mahotas as mh
import logging
import jtlib.utils

VERSION = '0.0.4'

logger = logging.getLogger(__name__)
PAD = 1

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


def main(input_mask, min_area, max_area, max_form_factor, max_solidity,
        plot=False):
    '''Selects clumped objects in `input_mask` based on the
    provided thresholds.

    Parameters
    ----------
    input_mask: numpy.ndarray[numpy.bool]
        2D binary array of potential clumps
    min_area: int
        minimal area an object must have to be considered a clump
    max_area: int
        maximal area an object must have to be considered a clump
    max_solidity: float
        maximal solidity an object must have to be considerd a clump
    max_form_factor: float
        maximal form factor an object must have to be considerd a clump

    Returns
    -------
    Dict[str, numpy.ndarray[numpy.bool] or str]
        * "output_mask": image with cut clumped objects
        * "figure": JSON figure representation
    '''
    label_image, n_objects = mh.label(input_mask)
    output_mask = np.zeros(input_mask.shape, input_mask.dtype)
    bboxes = mh.labeled.bbox(label_image)
    object_ids = np.unique(label_image[label_image > 0])
    for oid in object_ids:
        logger.debug('process object #%d', oid)
        mask = jtlib.utils.extract_bbox_image(
            label_image, bboxes[oid], pad=PAD
        )
        mask = mask == oid

        is_clump = False
        area, form_factor, solidity = calc_features(mask)
        if ((area > min_area or area < max_area) and
            (form_factor < max_form_factor) and
            (solidity < max_solidity)):
            logger.debug('clump')
            is_clump = True

        if is_clump:
            y, x = np.where(mask)
            y_offset, x_offset = bboxes[oid][[0, 2]] - PAD
            y += y_offset
            x += x_offset
            output_mask[y, x] = True

    output = dict()
    output['output_mask'] = output_mask
    if plot:
        from jtlib import plotting
        area_img, form_factor_img, solidity_img = create_feature_images(
            output_mask
        )
        area_colorscale = plotting.create_colorscale('Greens')
        form_factor_colorscale = plotting.create_colorscale('Blues')
        solidity_colorscale = plotting.create_colorscale('Reds')
        plots = [
            plotting.create_gadient_image_plot(
                area_img, 'ul', colorscale=area_colorscale
            ),
            plotting.create_gadient_image_plot(
                solidity_img, 'ur', colorscale=solidity_colorscale
            ),
            plotting.create_gadient_image_plot(
                form_factor_img, 'll', colorscale=form_factor_colorscale
            ),
            plotting.create_mask_image_plot(
                output_mask, 'lr'
            ),
        ]
        output['figure'] = plotting.create_figure(
            plots, title='separated clumps'
        )
    else:
        output['figure'] = str()

    return output
