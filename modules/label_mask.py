import matplotlib.pyplot as plt
import collections
import numpy as np
from jtlib import plotting
from jtlib import utils


def label_mask(mask, **kwargs):
    '''
    Jterator module for labeling objects (connected components)
    in a binary image.

    Parameters
    ----------
    mask: numpy.ndarray[bool]
        binary image that should labeled
    **kwargs: dict
        additional arguments provided by Jterator as key-value pairs:
        "data_file", "figure_file", "experiment_dir", "plot", "job_id"

    Returns
    -------
    collections.namedtuple[numpy.ndarray[int]]
        labeled image: "objects"

    Note
    ----
    If `mask` is not binary, it will be binarized, i.e. all pixel values above
    zero will be set to ``True`` and ``False`` otherwise.
    '''

    mask = mask > 0
    labeled_image = utils.label_image(mask)

    if kwargs['plot']:

        fig = plt.figure()
        ax1 = fig.add_subplot(1, 1, 1)

        img_obj = labeled_image.copy().astype(float)
        img_obj[labeled_image == 0] = np.nan

        ax1.imshow(img_obj, cmap=plt.cm.jet)
        ax1.set_title('labeled objects', size=20)

        fig.tight_layout()

        plotting.save_mpl_figure(fig, kwargs['figure_file'])

    output = collections.namedtuple('Output', 'objects')
    return output(labeled_image)
