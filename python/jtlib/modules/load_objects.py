import os
import logging
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
# import cv2
import mpld3
import collections
from jtlib import plotting
from tmlib.readers import DatasetReader
from tmlib.experiment import Experiment

logger = logging.getLogger(__name__)


def load_objects(objects_name, **kwargs):
    '''
    Jterator module for segmented objects as a labeled image from a HDF5 file
    on disk. Background is encoded with zeros and each object has a
    unique non-zero label.

    Parameters
    ----------
    objects_name: str
        name of the objects in the label image that should be loaded
    **kwargs: dict
        additional arguments provided by Jterator:
        "data_file", "figure_file", "experiment_dir", "plot", "job_id"

    Returns
    -------
    collections.namedtuple[numpy.ndarray[uint]]
        label image that encodes the objects: "loaded_objects"

    Warning
    -------
    You cannot load objects that were saved within the same pipeline, because
    objects will be retrieved from a joined data file that first needs to be
    created in the `collect` phase of the `jterator` step.

    See also
    --------
    :py:attr:`tmlib.experiment.Experiment.data_file`
    :py:class:`tmlib.layer.SegmentedObjectLayer`
    '''
    experiment = Experiment(kwargs['experiment_dir'])
    filename = os.path.join(experiment.dir, experiment.data_file)

    group_name = '/objects/%s/segmentation/%d' % (objects_name, kwargs['job_id'])

    with DatasetReader(filename) as f:
        labeled_image = f.read('%s/image' % group_name)

    logger.info('loaded %d "%s" objects',
                len(np.unique(labeled_image))-1, objects_name)

    # labeled_image = np.zeros((image_dim_y[0], image_dim_x[0]), dtype=np.int32)
    # for i in xrange(len(y_coordinates)):
    #     # NOTE: OpenCV wants (x, y) coordinates rather than (y, x) coordinates
    #     c = np.array(zip(x_coordinates[i], y_coordinates[i]), dtype=np.int32)
    #     print c
    #     # Labels are one-based (zero encodes for background pixels)
    #     cv2.fillConvexPoly(labeled_image, c, i+1)

    if kwargs['plot']:

        fig = plt.figure()
        ax = fig.add_subplot(1, 1, 1)

        img_obj = labeled_image.astype(float)
        img_obj[labeled_image == 0] = np.nan
        im = ax.imshow(img_obj)
        ax.set_title(objects_name, size=20)

        divider = make_axes_locatable(ax)
        cax = divider.append_axes("right", size="5%", pad=0.05)
        fig.colorbar(im, cax=cax)
        fig.tight_layout()

        mousepos = mpld3.plugins.MousePosition(fontsize=20)
        mpld3.plugins.connect(fig, mousepos)
        mpld3.fig_to_html(fig, template_type='simple')

        plotting.save_mpl_figure(fig, kwargs['figure_file'])

    Output = collections.namedtuple('Output', 'loaded_objects')
    return Output(labeled_image)
