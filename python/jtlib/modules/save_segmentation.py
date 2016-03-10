import numpy as np
import logging
import pandas as pd
import skimage.measure
from .. import utils

logger = logging.getLogger(__name__)


def save_segmentation(label_image, plot=False):
    '''
    Jterator module for saving segmented objects
    that were detected in an image,

    Parameters
    ----------
    label_image: numpy.ndarray[int32]
        labeled image where pixel value encodes objects id
    plot: bool, optional
        whether a plot should be generated (default: ``False``)
    '''
    objects_ids = np.unique(label_image[label_image > 0])
    border_indices = utils.find_border_objects(label_image)

    y_coordinates = list()
    x_coordinates = list()

    # Set border pixels to background to find complete contours of border objects
    label_image[0, :] = 0
    label_image[-1, :] = 0
    label_image[:, 0] = 0
    label_image[:, -1] = 0

    for obj_id in objects_ids:
        # Find the contours of the current object
        # We could do this for all objects at once, but doing it for each
        # object individually ensures that we get the correct number of objects
        # and that the coordinates are in the correct order, i.e. sorted by
        # label
        obj_im = label_image == obj_id
        contours = skimage.measure.find_contours(
                        obj_im, 0.5, fully_connected='high')
        if len(contours) > 1:
            logger.warn('%d contours identified for object #%d',
                        len(contours), obj_id)
        contour = contours[0]
        y = contour[:, 0].astype(np.int64)
        x = contour[:, 1].astype(np.int64)
        y_coordinates.append(y)
        x_coordinates.append(x)

    outlines = pd.DataFrame({'y': y_coordinates, 'x': x_coordinates})

    regions = skimage.measure.regionprops(label_image)
    if len(objects_ids) > 0:
        centroids = np.array([r.centroid for r in regions]).astype(np.int64)
    else:
        centroids = np.empty((0, 2)).astype(np.int64)

    centroids = pd.DataFrame(centroids)
    centroids.columns = ['y', 'x']

    output = {
        'centroids': centroids,
        'outlines': outlines,
        'is_border': border_indices
    }

    if plot:
        from .. import plotting

        outline_image = np.zeros(label_image.shape, dtype=np.int64)
        for i, obj in enumerate(objects_ids):
            outline_image[y_coordinates[i], x_coordinates[i]] = obj

        plots = [
            plotting.create_mask_image_plot(label_image, 'ul'),
            plotting.create_mask_image_plot(outline_image, 'ur')
        ]

        output['figure'] = plotting.create_figure(
                                plots,
                                title='Outlines of segmented objects')

    return output
