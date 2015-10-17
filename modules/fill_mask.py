from scipy import ndimage as ndi
import collections
import pylab as plt
from tmlib.jterator import jtapi


def fill_mask(mask, **kwargs):
    '''
    Jterator module to fill holes (enclosed pixel regions of connected components)
    in a binary image.

    Parameters
    ----------
    mask: numpy.ndarray
        binary image that should be filled
    **kwargs: dict
        additional arguments provided by Jterator:
        "data_file", "figure_file", "experiment_dir", "plot", "job_id"

    Returns
    -------
    namedtuple[numpy.ndarray[bool]]
        filled binary image: "filled_mask"
    '''
    img = ndi.binary_fill_holes(mask)

    if kwargs['plot']:

        fig = plt.figure(figsize=(10, 10))
        ax1 = fig.add_subplot(1, 2, 1)
        ax2 = fig.add_subplot(1, 2, 2)

        ax1.imshow(mask)
        ax1.set_title('input mask', size=20)

        ax2.imshow(img)
        ax2.set_title('filled mask', size=20)

        fig.tight_layout()

        jtapi.savefigure(fig, kwargs['figure_file'])

    output = collections.namedtuple('Output', 'filled_mask')
    return output(img)
