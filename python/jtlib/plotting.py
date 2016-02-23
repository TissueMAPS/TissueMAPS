import os
import mpld3
import numpy as np
import mahotas as mh
import plotly
from bokeh.resources import CDN
from bokeh.embed import file_html
from bokeh.palettes import Reds5, Greens5, Blues5, Oranges5, BuPu5
import matplotlib as mpl
from matplotlib import cm
import logging
from tmlib import image_utils
# from bokeh.embed import components

logger = logging.getLogger(__name__)


def save_mpl_figure(fig, figure_file):
    '''
    Write `mpld3 <http://mpld3.github.io/>`_ instance to file as HTML string
    with embedded javascript code.

    Parameters
    ----------
    fig: matplotlib.figure.Figure
        figure instance
    figure_file: str
        name of the figure file

    Note
    ----
    Also saves a thumbnail of the figure as PNG image.

    Warning
    -------
    Display of the figure in the browser requires internet connection, because
    the javascript library code is loaded via the web.
    See `troubleshooting <http://mpld3.github.io/faq.html#troubleshooting>`_.
    '''
    fig.figsize = (100, 100)
    mousepos = mpld3.plugins.MousePosition(fontsize=20)
    mpld3.plugins.connect(fig, mousepos)
    logger.debug('write figure to HTML file: "%s"' % figure_file)
    mpld3.save_html(fig, figure_file)   # template_type='simple'
    # Also save figure as image
    img_file = '%s.png' % os.path.splitext(figure_file)[0]
    fig.savefig(img_file)


def save_bokeh_figure(fig, figure_file):
    '''
    Write `bokeh <http://bokeh.pydata.org/en/latest/>`_ figure instance to
    file as HTML string with embedded javascript code.

    Parameters
    ----------
    fig: bokeh.plotting.Figure
        figure instance
    figure_file: str
        name of the figure file
    '''
    html = file_html(fig, resources=CDN, title='jterator figure')
    with open(figure_file, 'w') as f:
        f.write(html)


def save_plotly_figure(fig, figure_file):
    '''
    Write `plotly <https://plot.ly/python/>`_ figure instance to
    file as HTML string with embedded javascript code.

    Parameters
    ----------
    fig: plotly.graph_objs.Figure or plotly.graph_objs.Data
        figure instance
    figure_file: str
        name of the figure file
    '''
    fig['layout']['width'] = 800
    fig['layout']['height'] = 800
    # TODO: We have to include the library in order to be able to embed the
    # figure using <iframe>. The file would be way more light weight without,
    # but when we simply include the <div> on the client side, the dimensions
    # of the figure get completely screwed up. Maybe we can inject the library
    # code on the client side to reduce the amount of data we have to send.
    html = plotly.offline.plot(
            fig,
            output_type='div',
            include_plotlyjs=True,
            show_link=False
    )
    with open(figure_file, 'w') as f:
        f.write(html)
    # NOTE: Creation of static images requires "log-in".
    # img_file = '%s.png' % os.path.splitext(figure_file)[0]
    # plotly.plotly.image.save_as(fig, img_file)


def create_bokeh_palette(mpl_cmap):
    '''
    Convert a
    `matplotlib colormap <http://matplotlib.org/users/colormaps.html>`_
    to a HEX color palette as required by
    `bokeh <http://bokeh.pydata.org/en/latest/>`_.

    Parameters
    ----------
    mpl_cmap: matplotlib.colors.LinearSegmentedColormap
        matplotlib colormap

    Returns
    -------
    List[str]
        color palette

    Note
    ----
    Bokeh's build in palettes have only a few hues. If one wants to display
    values of a larger range one has to create a custom palette.
    '''
    colormap = cm.get_cmap(mpl_cmap)
    palette = [mpl.colors.rgb2hex(m) for m in colormap(np.arange(colormap.N))]
    return palette


def create_bk_image_overlay(image, mask, outlines=True,
                            color='red', transparency=0):
    '''
    Overlay a `mask` on a greyscale `image` by colorizing the pixels where
    `mask` is ``True`` according to `color` and all other pixels with shades of
    gray according to the values in `image`.

    For selection of colors see
    `html colors <http://www.w3schools.com/html/html_colors.asp>`_.

    Parameters
    ----------
    img: numpy.ndarray[uint16]
        intensity image
    mask: numpy.ndarray[bool]
        mask image
    outlines: bool, optional
        whether only the outlines should be overlayed (default: ``True``)
    color: str, optional
        "red", "green", "blue", "orange", or "purple" (default: ``"red"``)
    transparency: int, optional
        value between 0 and 5 (default: ``0``)

    Returns
    -------
    Tuple[numpy.ndarray, List[str]]
        image and corresponding palette

    Note
    ----
    `image` is converted to 8-bit.
    '''
    if color == 'red':
        color_palette = Reds5
    elif color == 'green':
        color_palette = Greens5
    elif color == 'purple':
        color_palette = BuPu5
    elif color == 'blue':
        color_palette = Blues5
    elif color == 'orange':
        color_palette = Oranges5
    else:
        raise ValueError(
                'Argument color has to be one of the following options: "%s"'
                % '", "'.join({'red', 'green', 'blue', 'orange', 'purple'}))

    if outlines:
        # Get the contours of the mask
        mask = mh.labeled.borders(mask)

    # Convert the image to 8-bit for display
    img_rescaled = image_utils.convert_to_uint8(image)

    # Bokeh cannot deal with RGB images in form of 3D numpy arrays.
    # Therefore, we have to work around it by adapting the color palette.
    img_rgb = img_rescaled.copy()
    img_rgb[img_rescaled == 255] = 254
    img_rgb[mask] = 255
    # border pixels will be colorized, all others get different shades of gray
    palette_grey = create_bokeh_palette('greys')
    palette_rgb = np.array(palette_grey)
    palette_rgb[-1] = color_palette[transparency]

    return (img_rgb, palette_rgb)
