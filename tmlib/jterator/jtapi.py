import mpld3
import numpy as np
import mahotas as mh
from bokeh.resources import CDN
from bokeh.plotting import save
from bokeh.palettes import Reds5, Greens5, Blues5, Oranges5, BuPu5
import matplotlib as mpl
from matplotlib import cm
import mpl.cm
import logging
from .. import image_utils
# import os
# import re
# from lxml import etree
# from bokeh.embed import components

logger = logging.getLogger(__name__)


def save_mpl_figure(fig, figure_file):
    '''
    Writing figure instance to file as HTML string with embedded javascript
    code using the `mpld3 <http://mpld3.github.io/>`_ library.

    Parameters
    ----------
    fig: matplotlib.figure.Figure
        figure instance
    figure_file: str
        name of the figure file

    Note
    ----
    Display of the figure in the browser requires internet connection.
    See `troubleshooting <http://mpld3.github.io/faq.html#troubleshooting>`_.
    '''
    mousepos = mpld3.plugins.MousePosition(fontsize=20)
    mpld3.plugins.connect(fig, mousepos)
    logger.debug('write figure to HTML file: "%s"' % figure_file)
    mpld3.save_html(fig, figure_file)   # template_type='simple'


def save_bokeh_figure(fig, figure_file):
    '''
    Writing figure instance to file as HTML string with embedded javascript
    code using the `bokeh <http://bokeh.pydata.org/en/latest/>`_ library.

    Parameters
    ----------
    fig: bokeh.plotting.Figure
        figure instance
    figure_file: str
        name of the figure file
    '''
    save(obj=fig, resources=CDN, filename=figure_file)

    # # One could modify the div element dynamically
    # script, div = components(fig)
    # html = etree.HTML(div)
    # html = etree.HTML(div)
    # for element in html.xpath('*/div'):
    #     element.attrib['ng-mouseover'] = ''
    # mod_div = etree.tostring(html, pretty_print=True, method='html')
    # with open(figure_file, 'w') as f:
    #     f.write(mod_div)
    # script_file = re.sub(r'(%s)$' % os.path.splitext(figure_file)[1],
    #                      '.script', figure_file)
    # with open(script_file, 'w') as f:
    #     f.write(script)


def create_bokeh_palette(mpl_cmap):
    '''
    Convert a `matplotlib colormap <http://matplotlib.org/users/colormaps.html>`_
    to a HEX color palette as required by bokeh.

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
    Bokeh's palettes have only a few hues. If one wants to display values
    of a larger range one has to create a custom palette.
    '''
    colormap = cm.get_cmap('gray')
    palette = [mpl.colors.rgb2hex(m) for m in colormap(np.arange(colormap.N))]
    return palette


def create_bokeh_overlay(image, mask, outlines=True,
                         color='red', transparency=0):
    '''
    Overlay a `mask` on a greyscale `image` by colorizing the pixels where
    `mask` is ``True`` according to `color`.

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
    # border pixels will be colored red, all others get gray colors
    grey_palette = create_bokeh_palette('greys')
    rgb_palette = np.array(grey_palette)
    rgb_palette[-1] = color_palette[transparency]

    return (img_rgb, rgb_palette)
