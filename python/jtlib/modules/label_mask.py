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
        from .. import plotting

        plots = [
            plotting.create_mask_image_plot(mask, 'ul'),
            plotting.create_mask_image_plot(labeled_image, 'ur')
        ]

        fig = plotting.create_figure(plots, title='Labeled objects in mask.')
        plotting.save_figure(fig, kwargs['figure_file'])

    Output = collections.namedtuple('Output', 'objects')
    return Output(labeled_image)
