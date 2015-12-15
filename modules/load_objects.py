import os
import numpy as np
import mahotas as mh
from scipy import ndimage as ndi
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
import mpld3
import collections
from jtlib import plotting
from tmlib.readers import DatasetReader
from tmlib.experiment import Experiment


def load_objects(objects_name, **kwargs):
    '''
    Jterator module for loading outline coordinates of segmented objects from
    a HDF5 file on disk. A mask image is then reconstructed from the outlines
    and labeled so that all pixels of an object (connected components) have a
    unique identifier number.

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
    '''
    experiment = Experiment(kwargs['experiment_dir'])
    filename = os.path.join(experiment.dir, experiment.data_file)

    # Does job_id do it? Consider matching metadata such site, channel, ...

    group_name = '/objects/%s/segmentation' % objects_name

    with DatasetReader(filename) as f:
        jobs = f.read('%s/job_ids' % group_name)
        job_ix = jobs == kwargs['job_id']
        y_coordinates = f.read('%s/outlines/y' % group_name, index=job_ix)
        x_coordinates = f.read('%s/outlines/x' % group_name, index=job_ix)
        image_dim_y = f.read('%s/image_dimensions/y' % group_name, index=job_ix)
        image_dim_x = f.read('%s/image_dimensions/x' % group_name, index=job_ix)

    outline_image = np.zeros((image_dim_y[0], image_dim_x[0]), dtype=np.int32)
    coordinates = zip(y_coordinates, x_coordinates)
    # for i, c in enumerate(coordinates):
    #     outline_image[c[0], c[1]] = i + 1
    for y, x in coordinates:
        outline_image[y, x] = 1

    # Fill objects
    mask_image = ndi.binary_fill_holes(outline_image)

    # Label the created mask
    labeled_image, n_objects = mh.label(mask_image)

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

    output = collections.namedtuple('Output', 'loaded_objects')
    return output(labeled_image)
