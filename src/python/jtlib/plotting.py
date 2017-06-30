# Copyright 2016 Markus D. Herrmann, University of Zurich
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import json
import numpy as np
import mahotas as mh
import plotly
import skimage
from matplotlib import cm
import logging

logger = logging.getLogger(__name__)

#: Color used to represented segmented objects in binary mask images
#: (on black background).
OBJECT_COLOR = 'rgb(255, 191, 0)'

#: Relative height of each plot within the figure.
PLOT_HEIGHT = 0.43

#: Relative width of each plot within the figure.
PLOT_WIDTH = 0.43

#: Absolute height of the figure in pixels.
FIGURE_HEIGHT = 800

#: Absolute width of the figure in pixels.
FIGURE_WIDTH = 800

#: Mapping for the position of the colorbar relative to the figure.
COLORBAR_POSITION_MAPPING = {
    "ul": (1-PLOT_HEIGHT, PLOT_WIDTH),
    "ur": (1-PLOT_HEIGHT, 1),
    "ll": (0, PLOT_WIDTH),
    "lr": (0, 1),
}

#: Mapping for the position of the plot relative to the figure.
PLOT_POSITION_MAPPING = {
    "ul": ('y1', 'x1'),
    "ur": ('y2', 'x2'),
    "ll": ('y3', 'x3'),
    "lr": ('y4', 'x4'),
}

#: The factor by which the size of an image should be reduced for plotting.
#: This helps reducing the amount of data that has to be send to the client.
IMAGE_RESIZE_FACTOR = 4


def _check_position_argument(position):
    supported_positions = {"ul", "ur", "ll", "lr"}
    if not isinstance(position, basestring):
        raise TypeError('Argument "position" must have type basestring.')
    if position not in supported_positions:
        raise ValueError(
            'A figure is a 2x2 grid of plots. '
            'Values of argument "position" must be either "%s"'
            % '", "'.join(supported_positions)
        )


def create_histogram_plot(data, position, color='grey'):
    '''Creates a histogram plot.

    Parameters
    ----------
    data: list or numpy.array
        data that should be plotted
    position: str
        coordinate that defines the relative position of the
        plot within the figure; ``"ul"`` -> upper left, ``"ur"`` -> upper
        right, ``"ll"`` lower left, ``"lr"`` -> lower right
    color: str, optional
        color that should be used for the marker

    Returns
    -------
    plotly.graph_objs.graph_objs.Histogram
    '''
    _check_position_argument(position)
    return plotly.graph_objs.Histogram(
        x=data,
        marker=dict(color=color),
        showlegend=False,
        yaxis=PLOT_POSITION_MAPPING[position][0],
        xaxis=PLOT_POSITION_MAPPING[position][1],
    )


def create_scatter_plot(y_data, x_data, position, color='grey', marker_size=4):
    '''Creates a scatter plot.

    Parameters
    ----------
    y_data: list or numpy.array
        data that should be plotted along the y-axis
    x_data: list or numpy.array
        data that should be plotted along the x-axis
    position: str
        coordinate that defines the relative position of the
        plot within the figure; ``"ul"`` -> upper left, ``"ur"`` -> upper
        right, ``"ll"`` lower left, ``"lr"`` -> lower right
    color: str, optional
        color of the points (default: ``"grey"``)
    marker_size: int, optional
        size of the points (default: ``4``)


    Returns
    -------
    plotly.graph_objs.graph_objs.Scatter
    '''
    _check_position_argument(position)
    return plotly.graph_objs.Scatter(
        y=y_data, x=x_data,
        marker=dict(size=marker_size, color=color),
        showlegend=False,
        yaxis=PLOT_POSITION_MAPPING[position][0],
        xaxis=PLOT_POSITION_MAPPING[position][1],
    )


def create_line_plot(y_data, x_data, position, color='grey', line_width=4):
    '''Creates a line plot.

    Parameters
    ----------
    y_data: list or numpy.array
        data that should be plotted along the y-axis
    x_data: list or numpy.array
        data that should be plotted along the x-axis
    position: str
        coordinate that defines the relative position of the
        plot within the figure; ``"ul"`` -> upper left, ``"ur"`` -> upper
        right, ``"ll"`` lower left, ``"lr"`` -> lower right
    color: str, optional
        color of the line (default: ``"grey"``)
    line_width: int, optional
        width of the line (default: ``4``)

    Returns
    -------
    plotly.graph_objs.graph_objs.Scatter
    '''
    _check_position_argument(position)
    return plotly.graph_objs.Scatter(
        y=y_data, x=x_data,
        marker=dict(size=0),
        line=dict(color=color, width=line_width),
        showlegend=False,
        yaxis=PLOT_POSITION_MAPPING[position][0],
        xaxis=PLOT_POSITION_MAPPING[position][1],
    )


def create_intensity_image_plot(image, position, clip=True, clip_value=None):
    '''Creates a heatmap plot for an intensity image.
    Intensity values will be encode with greyscale colors.

    Parameters
    ----------
    image: numpy.ndarray[numpy.uint8 or numpy.uint16]
        2D intensity image
    position: str
        coordinate that defines the relative position of the
        plot within the figure; ``"ul"`` -> upper left, ``"ur"`` -> upper
        right, ``"ll"`` lower left, ``"lr"`` -> lower right
    clip: bool, optional
        whether intensity values should be clipped (default: ``True``)
    clip_value: int, optional
        value above which intensity values should be clipped;
        the 99th percentile of intensity values will be used in case no value
        is provided; will only be considered when `clip` is ``True``
        (default: ``None``)

    Returns
    -------
    plotly.graph_objs.graph_objs.Heatmap

    See also
    --------
    :func:`jtlib.plotting.create_float_image_plot`
    :func:`jtlib.plotting.create_intensity_overlay_image_plot`
    '''

    _check_position_argument(position)
    if not str(image.dtype).startswith('uint'):
        raise TypeError('Argument "image" must have unsigned integer type.')

    block = (IMAGE_RESIZE_FACTOR, IMAGE_RESIZE_FACTOR)
    ds_img = skimage.measure.block_reduce(
        image, block, func=np.mean
    ).astype(int)

    if clip:
        if clip_value is None:
            clip_upper = round(np.percentile(image, 99))
        else:
            clip_upper = clip_value
    else:
        clip_upper = round(np.max(image))
    clip_lower = round(np.min(image))

    return plotly.graph_objs.Heatmap(
        z=ds_img,
        # Only show pixel intensities upon mouse hover.
        hoverinfo='z',
        # Background should be black and pixel intensities encode
        # as grey values.
        colorscale='Greys',
        # Rescale pixel intensity values for display.
        zmax=clip_upper,
        zmin=clip_lower,
        zauto=False,
        colorbar=dict(
            thickness=10,
            yanchor='bottom',
            y=COLORBAR_POSITION_MAPPING[position][0],
            x=COLORBAR_POSITION_MAPPING[position][1],
            len=PLOT_HEIGHT
        ),
        y=np.linspace(0, image.shape[0], ds_img.shape[0]),
        x=np.linspace(0, image.shape[1], ds_img.shape[1]),
        yaxis=PLOT_POSITION_MAPPING[position][0],
        xaxis=PLOT_POSITION_MAPPING[position][1],
    )


def create_float_image_plot(image, position, clip=True, clip_value=None):
    '''Creates a heatmap plot for a floating point image.

    Parameters
    ----------
    image: numpy.ndarray[numpy.float]
        2D floating point image
    position: str
        coordinate that defines the relative position of the
        plot within the figure; ``"ul"`` -> upper left, ``"ur"`` -> upper
        right, ``"ll"`` lower left, ``"lr"`` -> lower right
    clip: bool, optional
        whether intensity values should be clipped (default: ``True``)
    clip_value: int, optional
        value above which intensity values should be clipped;
        the 99th percentile of intensity values will be used in case no value
        is provided; will only be considered when `clip` is ``True``
        (default: ``None``)

    Returns
    -------
    plotly.graph_objs.graph_objs.Heatmap

    See also
    --------
    :func:`jtlib.plotting.create_intensity_image_plot`
    '''

    _check_position_argument(position)
    if image.dtype != float:
        raise TypeError('Argument "image" must have data type float.')

    block = (IMAGE_RESIZE_FACTOR, IMAGE_RESIZE_FACTOR)
    ds_img = skimage.measure.block_reduce(
        image, block, func=np.mean
    )

    if clip:
        if clip_value is None:
            clip_upper = np.percentile(image, 99.99)
        else:
            clip_upper = clip_value
    else:
        clip_upper = np.max(image)
    clip_lower = np.min(image)

    return plotly.graph_objs.Heatmap(
        z=ds_img,
        # Only show pixel intensities upon mouse hover.
        hoverinfo='z',
        # Background should be black and pixel intensities encode
        # as grey values.
        colorscale='Greys',
        zmax=clip_upper,
        zmin=clip_lower,
        zauto=False,
        colorbar=dict(
            thickness=10,
            yanchor='bottom',
            y=COLORBAR_POSITION_MAPPING[position][0],
            x=COLORBAR_POSITION_MAPPING[position][1],
            len=PLOT_HEIGHT
        ),
        y=np.linspace(0, image.shape[0], ds_img.shape[0]),
        x=np.linspace(0, image.shape[1], ds_img.shape[1]),
        yaxis=PLOT_POSITION_MAPPING[position][0],
        xaxis=PLOT_POSITION_MAPPING[position][1],
    )


def create_mask_image_plot(mask, position, colorscale=None):
    '''Creates a heatmap plot for a mask image.
    Unique object labels will be encoded with RGB colors.

    Parameters
    ----------
    mask: numpy.ndarray[numpy.bool or numpy.int32]
        binary or labeled 2D mask image
    position: str
        coordinate that defines the relative position of the
        plot within the figure; ``"ul"`` -> upper left, ``"ur"`` -> upper
        right, ``"ll"`` lower left, ``"lr"`` -> lower right
    colorscale: List[List[int, str]]
        colors that should be used to visually highlight the objects in the
        mask image; a default color map will be used if not provided;
        see `plotly docs <https://plot.ly/python/heatmap-and-contour-colorscales/>`_
        for more information of colorscale format (default: ``None``)

    Returns
    -------
    plotly.graph_objs.graph_objs.Heatmap

    See also
    --------
    :func:`jtlib.plotting.create_intensity_image_plot`
    :func:`jtlib.plotting.create_intensity_overlay_image_plot`
    '''
    _check_position_argument(position)
    # if not mask.dtype == np.bool or not mask.dtype == np.int32:
    #     raise TypeError('Argument "mask" must be binary.')

    block = (IMAGE_RESIZE_FACTOR, IMAGE_RESIZE_FACTOR)
    ds_mask = skimage.measure.block_reduce(
        mask, block, func=np.max
    ).astype(int)

    n_objects = len(np.unique(mask[mask > 0]))
    if colorscale is None:
        if n_objects == 1:
            colorscale = [[0, 'rgb(0,0,0)'], [1, OBJECT_COLOR]]
        elif n_objects == 0:
            colorscale = [[0, 'rgb(0,0,0)']]
        else:
            colorscale = create_colorscale('summer', n_objects)
            colorscale[0] = [0, 'rgb(0,0,0)']

    plot = plotly.graph_objs.Heatmap(
        z=ds_mask,
        colorscale=colorscale,
        hoverinfo='z',
        colorbar=dict(
            thickness=10,
            yanchor='bottom',
            y=COLORBAR_POSITION_MAPPING[position][0],
            x=COLORBAR_POSITION_MAPPING[position][1],
            len=PLOT_HEIGHT
        ),
        y=np.linspace(0, mask.shape[0], ds_mask.shape[0]),
        x=np.linspace(0, mask.shape[1], ds_mask.shape[1]),
        yaxis=PLOT_POSITION_MAPPING[position][0],
        xaxis=PLOT_POSITION_MAPPING[position][1],
    )

    if n_objects == 1:
        plot['colorbar'].update(tickmode='array', tickvals=[0, 1])

    return plot


def create_intensity_overlay_image_plot(image, mask, position,
        clip=True, clip_value=None, color=None):
    '''Creates an intensity image plot and overlays colorized mask outlines
    on top of the greyscale image.

    Parameters
    ----------
    image: numpy.ndarray[numpy.uint8 or numpy.uint16]
        2D intensity image
    position: str
        coordinate that defines the relative position of the
        plot within the figure; ``"ul"`` -> upper left, ``"ur"`` -> upper
        right, ``"ll"`` lower left, ``"lr"`` -> lower right
    clip: bool, optional
        whether intensity values should be clipped (default: ``True``)
    clip_value: int, optional
        value above which intensity values should be clipped;
        the 99th percentile of intensity values will be used in case no value
        is provided; will only be considered when `clip` is ``True``
        (default: ``None``)
    color: str, optional
        color of the mask outline; defaults to
        attribute:`jtlib.plotting.OBJECT_COLOR` in case no color
        is specified (default: ``None``)

    Returns
    -------
    plotly.graph_objs.graph_objs.Heatmap

    See also
    --------
    :func:`jtlib.plotting.create_intensity_image_plot`
    :func:`jtlib.plotting.create_mask_image_plot`
    '''

    _check_position_argument(position)
    if not mask.dtype == bool:
        raise TypeError('Argument "mask" must be binary.')
    if not str(image.dtype).startswith('uint'):
        raise TypeError('Argument "image" must have unsigned integer type.')

    block = (IMAGE_RESIZE_FACTOR, IMAGE_RESIZE_FACTOR)
    ds_mask = skimage.measure.block_reduce(
        mask, block, func=np.max
    )
    # We add 1 to each pixel value to make sure that there are no zeros
    # in the image. This is important because we will later consider all
    # zero pixels as outlines and colorize them accordingly (see below).
    ds_img = skimage.measure.block_reduce(
        image, block, func=np.mean
    ).astype(int) + 1
    ds_img[ds_mask] = 0

    if clip:
        if clip_value is None:
            clip_upper = round(np.percentile(image, 99.99))
        else:
            clip_upper = clip_value
    else:
        clip_upper = round(np.max(image))
    clip_lower = round(np.min(image))

    colorscale = create_colorscale('Greys', clip_upper - clip_lower)
    # Insert the color for the outlines into the colorscale. We insert it
    # at the end, but later reverse the scale for display, so zero values
    # in the image will be labeled with that color.
    if np.any(ds_mask):
        # Set outline pixel values to zero. We make sure that images
        # don't contain any zeros (see above).
        # Sweet! A nice side effect of this approach is that the outline color
        # will not be visible in the colorbar.
        if color is None:
            colorscale[-1][1] = OBJECT_COLOR
        else:
            colorscale[-1][1] = color

    return plotly.graph_objs.Heatmap(
        z=ds_img,
        # Only show pixel intensities upon mouse hover.
        hoverinfo='z',
        colorscale=colorscale,
        reversescale=True,
        # Rescale pixel intensity values for display.
        zmax=clip_upper,
        zmin=clip_lower,
        zauto=False,
        colorbar=dict(
            thickness=10,
            yanchor='bottom',
            y=COLORBAR_POSITION_MAPPING[position][0],
            x=COLORBAR_POSITION_MAPPING[position][1],
            len=PLOT_HEIGHT
        ),
        y=np.linspace(0, image.shape[0], ds_img.shape[0]),
        x=np.linspace(0, image.shape[1], ds_img.shape[1]),
        yaxis=PLOT_POSITION_MAPPING[position][0],
        xaxis=PLOT_POSITION_MAPPING[position][1],
    )


def create_mask_overlay_image_plot(mask, mask2, position, color=None):
    '''Creates an mask image plot and overlays colorized mask outlines
    on top of the binary image.

    Parameters
    ----------
    mask: numpy.ndarray[numpy.bool]
        2D mask image
    outlines: numpy.ndarray[numpy.bool]
        2D mask image that should be overlayed
    position: str
        coordinate that defines the relative position of the
        plot within the figure; ``"ul"`` -> upper left, ``"ur"`` -> upper
        right, ``"ll"`` lower left, ``"lr"`` -> lower right
    color: str, optional
        color of the mask outline; defaults to
        attribute:`jtlib.plotting.OBJECT_COLOR` in case no color
        is specified (default: ``None``)

    Returns
    -------
    plotly.graph_objs.graph_objs.Heatmap

    See also
    --------
    :func:`jtlib.plotting.create_mask_image_plot`
    '''

    _check_position_argument(position)
    if not mask.dtype == bool:
        raise TypeError('Argument "mask" must be binary.')
    if not mask2.dtype == bool:
        raise TypeError('Argument "mask2" must be binary.')

    block = (IMAGE_RESIZE_FACTOR, IMAGE_RESIZE_FACTOR)
    ds_mask = skimage.measure.block_reduce(
        mask, block, func=np.max
    ).astype(int)
    ds_mask2 = skimage.measure.block_reduce(
        mask2, block, func=np.max
    )
    ds_mask[ds_mask2] = 3

    if not np.any(ds_mask2):
        colorscale = [
            [0, 'rgb(0,0,0)'],
            [1, 'rgb(255, 255, 255)'],
        ]
    else:
        colorscale = [
            [0, 'rgb(0,0,0)'],
            [0.5, 'rgb(255, 255, 255)'],
            [1, OBJECT_COLOR]
        ]
        # Insert the color for the outlines into the colorscale. We insert it
        # at the end, but later reverse the scale for display, so zero values
        # in the image will be labeled with that color.
        if color:
            colorscale[-1][1] = color



    return plotly.graph_objs.Heatmap(
        z=ds_mask,
        colorscale=colorscale,
        showscale=False,
        y=np.linspace(0, mask.shape[0], ds_mask.shape[0]),
        x=np.linspace(0, mask.shape[1], ds_mask.shape[1]),
        yaxis=PLOT_POSITION_MAPPING[position][0],
        xaxis=PLOT_POSITION_MAPPING[position][1],
    )


def create_figure(plots, plot_positions=["ul", "ur", "ll", "lr"],
                  plot_is_image=[True, True, True, True], title=''):
    '''Creates a figure based on one or more subplots. Plots will be arranged as
    a 2x2 grid.

    Parameters
    ----------
    plots: List[plotly.graph_objs.Plot or List[plotly.graph_objs.Plot]]
        subplots that should be used in the figure; subplots can be further
        nested, i.e. grouped together in case they should be combined at the
        same figure position
    plot_positions: List[str], optional
        relative position of each plot in the figure;
        ``"ul"`` -> upper left, ``"ur"`` -> upper
        right, ``"ll"`` lower left, ``"lr"`` -> lower right
        (default: ``["ul", "ur", "ll", "lr"]``)
    plot_is_image: List[bool], optional
        whether a plot represents an image; for images the y axis is inverted
        accounting for the fact that the 0,0 coordinate is located in
        the upper left corner of the plot rather than in the default lower left
        corner (default: ``[True, True, True, True]``)
    title: str, optional
        title for the figure

    Returns
    -------
    str
        JSON string representation of the figure

    Raises
    ------
    TypeError
        when `plot`, `plot_positions`, or `plot_is_image` don't have type list
    ValueError
        when length of `plot`, `plot_positions`, or `plot_is_image` is larger
        than 4
    '''
    args_to_check = [plots, plot_positions, plot_is_image]
    if not all([isinstance(arg, list) for arg in args_to_check]):
        raise TypeError(
            'Arguments "%s" must have type list.'
            % '", "'.join(args_to_check)
        )
    if any([len(arg) > 4 for arg in args_to_check]) == 1:
        raise ValueError(
            'Arguments "%s" can have maximally length 4.'
            % '", "'.join(args_to_check)
        )

    data = list()
    layout = plotly.graph_objs.Layout(title=title)
    for i, p in enumerate(plots):
        if plot_positions[i] == "ul":
            layout.update(
                xaxis1=dict(domain=[0, PLOT_WIDTH], anchor='y1'),
                yaxis1=dict(domain=[1-PLOT_HEIGHT, 1], anchor='x1')
            )
            if plot_is_image[i]:
                layout['yaxis1']['autorange'] = 'reversed'
        elif plot_positions[i] == "ur":
            layout.update(
                xaxis2=dict(domain=[1-PLOT_WIDTH, 1], anchor='y2'),
                yaxis2=dict(domain=[1-PLOT_HEIGHT, 1], anchor='x2')
            )
            if plot_is_image[i]:
                layout['yaxis2']['autorange'] = 'reversed'
        elif plot_positions[i] == "ll":
            layout.update(
                xaxis3=dict(domain=[0, PLOT_WIDTH], anchor='y3'),
                yaxis3=dict(domain=[0, PLOT_HEIGHT], anchor='x3')
            )
            if plot_is_image[i]:
                layout['yaxis3']['autorange'] = 'reversed'
        elif plot_positions[i] == "lr":
            layout.update(
                xaxis4=dict(domain=[1-PLOT_WIDTH, 1], anchor='y4'),
                yaxis4=dict(domain=[0, PLOT_HEIGHT], anchor='x4')
            )
            if plot_is_image[i]:
                layout['yaxis4']['autorange'] = 'reversed'
        else:
            raise ValueError(
                'Options for values of argument "plot_positions" are: %s'
                % ', '.join(map(str, ["ul", "ur", "ll", "lr"]))
            )

        # Flatten potentially nested list
        if isinstance(p, list):
            data.extend(p)
        else:
            data.append(p)

    fig = plotly.graph_objs.Figure(data=data, layout=layout)
    fig['layout']['width'] = FIGURE_WIDTH
    fig['layout']['height'] = FIGURE_HEIGHT

    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


# def save_figure(fig, figure_file):
#     '''
#     Write `plotly <https://plot.ly/python/>`_ figure instance to
#     file as HTML string with embedded javascript code.

#     Parameters
#     ----------
#     fig: plotly.graph_objs.Figure
#         figure instance
#     figure_file: str
#         name of the figure file
#     '''
#     fig['layout']['width'] = 800
#     fig['layout']['height'] = 800
#     # TODO: We have to include the library in order to be able to embed the
#     # figure using <iframe>. The file would be way more light weight without,
#     # but when we simply include the <div> on the client side, the dimensions
#     # of the figure get completely screwed up. Maybe we can inject the library
#     # code on the client side to reduce the amount of data we have to send.
#     html = plotly.offline.plot(
#             fig,
#             output_type='div',
#             include_plotlyjs=True,
#             show_link=False,
#     )
#     with open(figure_file, 'w') as f:
#         f.write(html)
#     # NOTE: Creation of static images requires "log-in".
#     # img_file = '%s.png' % os.path.splitext(figure_file)[0]
#     # plotly.plotly.image.save_as(fig, img_file)


def create_colorscale(name, n=256, permute=False, add_background=False,
        background_color='black'):
    '''Creates a color palette in the format required by
    `plotly <https://plot.ly/python/>`_ based on a
    `matplotlib colormap <http://matplotlib.org/users/colormaps.html>`_.
    Please refer to
    `plotly docs <https://plot.ly/python/heatmap-and-contour-colorscales/>`_
    for more information on colorscale format.

    Parameters
    ----------
    name: str
        name of a matplotlib colormap, e.g. ``"Greys"``
    n: int
        number of colors (default: ``256``)
    permute: bool, optional
        whether colors should be randomly permuted (default: ``False``)
    add_background: bool, optional
        whether a value for background should be prepented to the colorscale
        (default: ``False``)
    background_color: str, optional
        whether "black" or "white" background should be used
        (default: ``"black"``)

    Returns
    -------
    List[List[float, str]]
        RGB color palette

    Examples
    --------
    >>> create_colorscale('Greys', 5)
    [[0.0,  'rgb(255,255,255)'],
     [0.25, 'rgb(216,216,216)'],
     [0.5,  'rgb(149,149,149)'],
     [0.75, 'rgb(82,82,82)'],
     [1.0,  'rgb(0,0,0)']]

    Notes
    -----
    You can invert a colorscale in a `plotly` graph using the
    :attr:`reversescale` argument.
    '''
    cmap = cm.get_cmap(name)
    if add_background:
        n += 1
    indices = np.round(np.linspace(0, 255, n)).astype(int)
    vals = np.linspace(0, 1, n)
    rgb_values = (cmap(indices)[:, 0:3] * 255).astype(int)
    if permute:
        rgb_values = np.random.permutation(rgb_values)
    colors = [
        [vals[i], 'rgb(%d,%d,%d)' % tuple(v)]
        for i, v in enumerate(rgb_values)
    ]
    if add_background:
        if background_color == 'black':
            colors[0] = [0, 'rgb(0,0,0)']
        elif background_color == 'white':
            colors[0] = [0, 'rgb(255,255,255)']
        else:
            raise ValueError(
                'Argument "background_color" can be either "black" or "white"'
            )

    return colors
