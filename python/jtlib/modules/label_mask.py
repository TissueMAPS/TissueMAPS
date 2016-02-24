import logging
import collections
import numpy as np
from .. import utils

logger = logging.getLogger(__name__)


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
    If `mask` is not binary, it will be binarized, i.e. pixels will be set to
    ``True`` if values are greater than zero and ``False`` otherwise.
    '''

    mask = mask > 0
    labeled_image = utils.label_image(mask)

    logger.info('identified %d objects', len(np.unique(labeled_image))-1)

    if kwargs['plot']:
        import matplotlib.pyplot as plt
        from .. import plotting

        fig = plt.figure()
        ax1 = fig.add_subplot(1, 1, 1)

        img_obj = labeled_image.astype(float)
        img_obj[labeled_image == 0] = np.nan

        ax1.imshow(img_obj, cmap=plt.cm.jet, interpolation='none')
        ax1.set_title('labeled objects', size=20)

        fig.tight_layout()

        plotting.save_mpl_figure(fig, kwargs['figure_file'])

    Output = collections.namedtuple('Output', 'objects')
    return Output(labeled_image)
