import pylab as plt
import collections
from tmlib.jterator import jtapi
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
    namedtuple[numpy.ndarray[int]]
        labeled image: "objects"

    Note
    ----
    If `mask` is not binary, it will be binarized, i.e. all pixel values above
    zero will be set to ``True`` and ``False`` otherwise.
    '''

    mask = mask > 0
    labeled_image = utils.label_image(mask)

    if kwargs['plot']:

        fig = plt.figure(figsize=(10, 10))
        ax1 = fig.add_subplot(1, 2, 1)
        ax2 = fig.add_subplot(1, 2, 2)

        ax1.imshow(mask)
        ax1.set_title('input image', size=20)

        ax2.imshow(labeled_image)
        ax2.set_title('labeled objects', size=20)

        fig.tight_layout()

        jtapi.savefigure(fig, kwargs['figure_file'])

    output = collections.namedtuple('Output', 'objects')
    return output(labeled_image)
