import numpy as np
import pylab as plt
from skimage import measure, morphology
from tmlib.writers import DatasetWriter
from tmlib.illuminati import segment
from tmlib.image_utils import find_border_objects
from tmlib.jterator import jtapi


def save_segmentation(labeled_image, objects_name, **kwargs):
    '''
    Jterator module for saving segmented objects. The outline coordinates get
    written to a HDF5 file as a *variable_length* dataset.

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

    border_indices = find_border_objects(labeled_image)

    regions = measure.regionprops(labeled_image)
    centroids = np.array([r.centroid for r in regions])

    with DatasetWriter(kwargs['data_file'], truncate=True) as f:
        f.write('objects/%s/object_ids' % objects_name,
                data=objects_ids)
        f.write('objects/%s/is_border' % objects_name,
                data=border_indices)
        f.write('objects/%s/site_ids' % objects_name,
                data=[kwargs['job_id'] for x in xrange(len(objects_ids))])
        f.write('objects/%s/segmentations/image_dimensions/y' % objects_name,
                data=labeled_image.shape[0])
        f.write('objects/%s/segmentations/image_dimensions/x' % objects_name,
                data=labeled_image.shape[1])
        f.write('objects/%s/segmentations/outlines/y' % objects_name,
                data=y_coordinates)
        f.write('objects/%s/segmentations/outlines/x' % objects_name,
                data=x_coordinates)
        f.write('objects/%s/segmentations/centroids/y' % objects_name,
                data=centroids[:, 0])
        f.write('objects/%s/segmentations/centroids/x' % objects_name,
                data=centroids[:, 1])

    if kwargs['plot']:

        n_objects = len(objects_ids)
        outline_image = np.zeros(labeled_image.shape)
        rand_num = np.random.randint(1, n_objects, size=n_objects)
        for i in xrange(n_objects):
            outline_image[y_coordinates[i], x_coordinates[i]] = rand_num[i]
        outline_image[outline_image == 0] = np.nan

        fig = plt.figure(figsize=(10, 10))
        ax1 = fig.add_subplot(1, 1, 1)

        ax1.imshow(outline_image)
        ax1.set_title(objects_name, size=20)

        fig.tight_layout()

        jtapi.save_mpl_figure(fig, kwargs['figure_file'])
