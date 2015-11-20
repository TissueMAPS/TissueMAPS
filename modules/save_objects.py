import numpy as np
import matplotlib.pyplot as plt
from skimage import measure
from tmlib.writers import DatasetWriter
from tmlib.illuminati import segment
from tmlib.image_utils import find_border_objects
from jtlib import plotting


def save_objects(image, name, **kwargs):
    '''
    Jterator module for saving segmented objects. The outline coordinates get
    written to a HDF5 file as a *variable_length* dataset.

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
    objects_ids = np.unique(image[image != 0])
    y_coordinates = list()
    x_coordinates = list()
    outline_image = segment.compute_outlines_numpy(
                        image, keep_ids=True)

    for obj_id in objects_ids:
        coordinates = np.where(outline_image == obj_id)
        y_coordinates.append(coordinates[0])  # row
        x_coordinates.append(coordinates[1])  # column

    # NOTE: Storing the outline coordinates per object works fine as long as
    # there are only a few (hundreds) of large objects, but it gets crazy for
    # a large number (thousands) of small objects.
    # Storing the actual image directly would be way faster in these cases,
    # but it would cost a lot more memory.

    border_indices = find_border_objects(image)

    regions = measure.regionprops(image)
    centroids = np.array([r.centroid for r in regions])

    if len(objects_ids) > 0:

        group_name = '/objects/%s/segmentation' % name

        with DatasetWriter(kwargs['data_file']) as f:
            f.write('%s/object_ids' % group_name,
                    data=objects_ids)
            f.write('%s/is_border' % group_name,
                    data=border_indices)
            f.write('%s/site_ids' % group_name,
                    data=[kwargs['job_id'] for x in xrange(len(objects_ids))])
            f.write('%s/image_dimensions/y' % group_name,
                    data=image.shape[0])
            f.write('%s/image_dimensions/x' % group_name,
                    data=image.shape[1])
            f.write('%s/outlines/y' % group_name,
                    data=y_coordinates)
            f.write('%s/outlines/x' % group_name,
                    data=x_coordinates)
            f.write('%s/centroids/y' % group_name,
                    data=centroids[:, 0])
            f.write('%s/centroids/x' % group_name,
                    data=centroids[:, 1])

    if kwargs['plot']:

        n_objects = len(objects_ids)
        outline_image = np.zeros(image.shape)
        if n_objects > 0:
            rand_num = np.random.randint(1, n_objects, size=n_objects)
            for i in xrange(n_objects):
                outline_image[y_coordinates[i], x_coordinates[i]] = rand_num[i]
        outline_image[outline_image == 0] = np.nan

        fig = plt.figure()
        ax1 = fig.add_subplot(1, 1, 1)

        ax1.imshow(outline_image)
        ax1.set_title('Outlines of objects "%s"' % name, size=20)

        fig.tight_layout()

        plotting.save_mpl_figure(fig, kwargs['figure_file'])
