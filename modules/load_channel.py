import numpy as np
from matplotlib import pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
import collections
import mpld3
from jterator import jtapi
import tmt
from tmt.image import ChannelImage


def load_channel(ImageFilename, Config=None, **kwargs):
    '''
    Jterator module for loading a "channel" image
    from disk into memory in order to make it available to downstream modules.

    .. Note::

        Images must have dtype "float64". This may be required for rescaling
        or other operations that wouldn't work with integer data types.

    Parameters
    ----------
    ChannelName: str
        name of the channel that should be loaded
    Config: str, optional
        configuration settings in form of a YAML string
    **kwargs: dict
        additional arguments provided by Jterator:
        "ProjectDir", "DataFile", "FigureFile", "Plot"

    Returns
    -------
    namedtuple[numpy.ndarray[float64]]
        loaded greyscale image: "LoadedImage"

    See also
    --------
    `image.ChannelImage`
    '''
    if Config:
        cfg = jtapi.readconfig(Config)
    else:
        cfg = tmt.config

    # overwrite configuration to enforce use of numpy
    cfg['USE_VIPS_LIBRARY'] = False

    # load image
    img = ChannelImage(ImageFilename, cfg).image

    if kwargs['Plot']:

        fig = plt.figure(figsize=(10, 10))
        ax = fig.add_subplot(1, 1, 1)

        min_rescale = np.percentile(img, 0.1)
        max_rescale = np.percentile(img, 99.9)

        im = ax.imshow(img, cmap='gray', vmin=min_rescale, vmax=max_rescale)
        ax.set_title(ImageFilename, size=20)

        divider = make_axes_locatable(ax)
        cax = divider.append_axes("right", size="5%", pad=0.05)
        fig.colorbar(im, cax=cax)
        fig.tight_layout()

        mousepos = mpld3.plugins.MousePosition(fontsize=20)
        mpld3.plugins.connect(fig, mousepos)
        mpld3.fig_to_html(fig, template_type='simple')

        jtapi.savefigure(fig, kwargs['FigureFile'])

    output = collections.namedtuple('Output', 'LoadedImage')
    return output(img)
