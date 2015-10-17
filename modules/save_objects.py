import numpy as np
from tmlib.writers import DatasetWriter
from tmlib.illuminati import segment


def save_objects(labeled_image, objects_name, **kwargs):
    '''
    Jterator module for saving objects. The outline coordinates get written
    to a HDF5 file as a *variable_length* dataset.

    Parameters
    ----------
    labeled_image: numpy.ndarray
        labeled image where pixel value encodes objects id
    objects_name: str
        name that should be given to the objects in `labeled_image`
    **kwargs: dict
        additional arguments provided by Jterator:
        "data_file", "figure_file", "experiment_dir", "plot", "job_id"
    '''
    objects_ids = np.unique(labeled_image[labeled_image != 0])
    y_coordinates = list()
    x_coordinates = list()
    outline_image = segment.compute_outlines_numpy(
                        labeled_image, keep_ids=True)

    for obj_id in objects_ids:
        coordinates = np.where(outline_image == obj_id)
        y_coordinates.append(coordinates[0])  # row
        x_coordinates.append(coordinates[1])  # column

    # NOTE: Storing the outline coordinates per object works fine as long as
    # there are only a few (hundreds) of large objects, but it gets crazy for
    # a large number (thousands) of small objects.
    # Storing the actual image directly would be way faster in these cases,
    # but it would cost a lot more memory.

    with DatasetWriter(kwargs['data_file'], truncate=True) as f:
        f.write('%s/segmentation/site_ids' % objects_name,
                data=[kwargs['job_id'] for x in xrange(len(objects_ids))])
        f.write('%s/segmentation/object_ids' % objects_name,
                data=objects_ids)
        f.write('%s/segmentation/image_dimensions/y' % objects_name,
                data=labeled_image.shape[0])
        f.write('%s/segmentation/image_dimensions/x' % objects_name,
                data=labeled_image.shape[1])
        f.write('%s/segmentation/coordinates/y' % objects_name,
                data=y_coordinates)
        f.write('%s/segmentation/coordinates/x' % objects_name,
                data=x_coordinates)
