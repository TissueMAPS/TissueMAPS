import numpy as np
import matplotlib.pyplot as plt
from skimage.measure import find_contours
from tmlib.writers import DatasetWriter
from skimage import measure
from tmlib.image_utils import find_border_objects
from jtlib import plotting


def save_objects(image, name, **kwargs):
    '''
    Jterator module for saving segmented objects. The outline coordinates are
    written to a HDF5 file and can be retrieved to reconstruct the labeled
    `image`.

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

    print 'WARNING: The retrieval of the objects doesn\'t work reliably!!!'

    # NOTE: Looping over individual objects ensures the correct total number of
    # objects and the correct assignment of object IDs.
    # Using find_contours() directly gives wrong results.

    border_indices = find_border_objects(image)

    # Set border pixels to background to find complete contours of border objects
    image[0, :] = 0
    image[-1, :] = 0
    image[:, 0] = 0
    image[:, -1] = 0

    # TODO: this padding should be done in each measurement module, too

    for obj_id in objects_ids:
        # Find the contours of the current object
        # NOTE: Points need to be provided in counter-clockwise order, which
        # is ensured by find_contours().
        im = image == obj_id
        contours = find_contours(im, 0.5)[0]
        # Calculate coordinates
        y = contours[:, 0].astype(np.int64)
        x = contours[:, 1].astype(np.int64)
        y_coordinates.append(y)
        x_coordinates.append(x)

    # NOTE: Storing the outline coordinates per object works fine as long as
    # there are only a few (hundreds) of large objects, but it can go crazy for
    # a large number (thousands) of small objects.
    # Storing the actual image directly would be way faster in these cases,
    # but it would cost a lot more memory.

    regions = measure.regionprops(image)
    centroids = np.array([r.centroid for r in regions]).astype(np.int64)

    group_name = '/objects/%s/segmentation' % name

    if len(objects_ids) > 0:

        with DatasetWriter(kwargs['data_file']) as f:
            f.write('%s/object_ids' % group_name,
                    data=objects_ids)
            f.write('%s/is_border' % group_name,
                    data=border_indices)
            f.write('%s/job_ids' % group_name,
                    data=[kwargs['job_id'] for x in xrange(len(objects_ids))])
            f.write('%s/image_dimensions/y' % group_name,
                    data=np.repeat(image.shape[0], len(objects_ids)))
            f.write('%s/image_dimensions/x' % group_name,
                    data=np.repeat(image.shape[1], len(objects_ids)))
            f.write('%s/outlines/y' % group_name,
                    data=y_coordinates)
            f.write('%s/outlines/x' % group_name,
                    data=x_coordinates)
            f.write('%s/centroids/y' % group_name,
                    data=centroids[:, 0])
            f.write('%s/centroids/x' % group_name,
                    data=centroids[:, 1])

    else:

        with DatasetWriter(kwargs['data_file']) as f:
            f.write('%s/object_ids' % group_name,
                    data=list())
            f.write('%s/is_border' % group_name,
                    data=list())
            f.write('%s/job_ids' % group_name,
                    data=list())
            f.write('%s/image_dimensions/y' % group_name,
                    data=list())
            f.write('%s/image_dimensions/x' % group_name,
                    data=list())
            f.write('%s/outlines/y' % group_name,
                    data=list())
            f.write('%s/outlines/x' % group_name,
                    data=list())
            f.write('%s/centroids/y' % group_name,
                    data=list())
            f.write('%s/centroids/x' % group_name,
                    data=list())

    if kwargs['plot']:

        n_objects = len(objects_ids)
        outline_image = np.zeros(image.shape)
        if n_objects > 1:
            rand_num = np.random.randint(1, n_objects, size=n_objects)
            for i in xrange(n_objects):
                outline_image[y_coordinates[i], x_coordinates[i]] = rand_num[i]
        elif n_objects == 1:
            outline_image[y_coordinates[0], x_coordinates[0]] = 1
        outline_image[outline_image == 0] = np.nan

        fig = plt.figure()
        ax1 = fig.add_subplot(1, 1, 1)

        ax1.imshow(outline_image)
        ax1.set_title('Outlines of objects "%s"' % name, size=20)

        fig.tight_layout()

        plotting.save_mpl_figure(fig, kwargs['figure_file'])
