import logging
import numpy as np
from .. import utils

logger = logging.getLogger(__name__)


def label_mask(mask, plot=False):
    '''
    Jterator module for labeling objects (connected components)
    in a binary image.

    Parameters
    ----------
    mask: numpy.ndarray[bool]
        binary image that should labeled
    plot: bool, optional
        whether a plot should be generated (default: ``False``)
    Returns
    -------
    Dict[str, numpy.ndarray[numpy.int32]]
        "label_image": labeled image
        "figure": html string in case ``kwargs["plot"] == True``

    Note
    ----
    If `mask` is not binary, it will be binarized, i.e. pixels will be set to
    ``True`` if values are greater than zero and ``False`` otherwise.
    '''

    mask = mask > 0
    label_image = utils.label_image(mask)

    logger.info('identified %d objects', len(np.unique(label_image))-1)

    output = {'label_image': label_image}
    if plot:
        from .. import plotting

        plots = [
            plotting.create_mask_image_plot(mask, 'ul'),
            plotting.create_mask_image_plot(label_image, 'ur')
        ]

        output['figure'] = plotting.create_figure(
                                plots, title='Labeled objects in mask.')
    else:
        output['figure'] = str()

    return output
