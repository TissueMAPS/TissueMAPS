import numpy as np
import logging
from skimage.measure import regionprops
from tmlib.writers import DatasetWriter
from tmlib.image_utils import find_border_objects

logger = logging.getLogger(__name__)


def save_objects(image, name, **kwargs):
    '''
    Jterator module for saving a segmentation image, i.e. a labeled image where
    each label encode a segmented object.

    Parameters
    ----------
    image: numpy.ndarray
        labeled image where pixel value encodes objects id
    name: str
        name that should be given to the objects in `image`
    **kwargs: dict
        additional arguments provided by Jterator:
        "data_file", "figure_file", "experiment_dir", "plot", "job_id"
    '''
    objects_ids = np.unique(image[image > 0])

    border_indices = find_border_objects(image)

    regions = regionprops(image)
    if len(objects_ids) > 0:
        centroids = np.array([r.centroid for r in regions]).astype(np.int64)
    else:
        centroids = np.empty((0, 2)).astype(np.int64)

    group_name = '/objects/%s/segmentation' % name

    if len(objects_ids) > 0:

        logger.info('save %d "%s" objects', len(objects_ids), name)

        with DatasetWriter(kwargs['data_file']) as f:
            f.write('%s/is_border' % group_name, data=border_indices)
            f.write('%s/centroids' % group_name, data=centroids)
            f.set_attribute('%s/centroids' % group_name, 'columns', ['y', 'x'])
            f.write('%s/image' % group_name, data=image)

    else:

        logger.info('no "%s" objects to be saved', name)

        with DatasetWriter(kwargs['data_file']) as f:
            f.write('%s/is_border' % group_name, data=list())
            f.write('%s/centroids' % group_name, data=centroids)
            f.set_attribute('%s/centroids' % group_name, 'columns', ['y', 'x'])
            f.write('%s/image' % group_name, data=image)
