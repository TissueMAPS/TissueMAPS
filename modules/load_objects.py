import numpy as np
import mahotas as mh
from scipy import ndimage as ndi
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
import mpld3
import collections
from jtlib import plotting
from tmlib.readers import DatasetReader
from tmlib.experiment import ExperimentFactory
from tmlib import cfg


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
    experiment = ExperimentFactory(kwargs['experiment_dir'], cfg).create()

    # Does job_id do it? Consider matching metadata such site, channel, ...

    with DatasetReader(experiment.data_file) as f:
        sites = f.read('%s/segmentation/site_ids' % objects_name)
        site_index = sites == kwargs['job_id']
        y_coordinates = f.read('%s/segmentation/coordinates/y' % objects_name,
                               index=site_index)
        x_coordinates = f.read('%s/segmentation/coordinates/x' % objects_name,
                               index=site_index)
        image_dims = f.read('%s/segmentation/image_dimensions' % objects_name,
                            index=site_index)

    outline_image = np.zeros(image_dims)
    outline_image[y_coordinates, x_coordinates] = 1
    mask_image = ndi.binary_fill_holes(outline_image)
    labeled_image, n_objects = mh.label(mask_image)

    if kwargs['plot']:

        fig = plt.figure()
        ax = fig.add_subplot(1, 1, 1)

        im = ax.imshow(labeled_image)
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
