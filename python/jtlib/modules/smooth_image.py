import cv2
from skimage.morphology import disk
from skimage.filters.rank import median
from skimage.filters.rank import mean_bilateral
from skimage.measure import block_reduce
import collections
import numpy as np
import plotly
from jtlib import plotting


def smooth_image(image, filter_name, filter_size, sigma=0, sigma_color=0,
                 sigma_space=0, **kwargs):
    '''
    Jterator module for smoothing an image.

    For more information on "average", "gaussian" and "bilateral" filters see
    `OpenCV tutorial <http://opencv-python-tutroals.readthedocs.org/en/latest/py_tutorials/py_smoothed_imageproc/py_filtering/py_filtering.html>`_.

    For more information on "median" filter_name see
    `scikit-image docs <http://scikit-image.org/docs/dev/api/skimage.filters.html#median>`_.


    Parameters
    ----------
    image: numpy.ndarray
        grayscale image that should be smoothed
    filter_name: str
        name of the filter kernel that should be applied
        (options: ``{"avarage", "gaussian", "median", "median-bilateral", "gaussian-bilateral"}``)
    filter_size: int
        size (width/height) of the kernel (must be positive and odd)
    sigma: int, optional
        standard deviation of the Gaussian kernel - only relevant for
        "gaussian" filter_name (default: ``0``)
    sigma_color: int, optional
        Gaussian component (filter_name sigma) applied in the intensity domain
        (color space) - only relevant for "bilateral" filter_name (default: ``0``)
    sigma_space: int, optional
        Gaussian component (filter_name sigma) applied in the spacial domain
        (coordinate space) - only relevant for "bilateral" filter_name
        (default: ``0``)
    **kwargs: dict
        additional arguments provided by Jterator:
        "data_file", "figure_file", "experiment_dir", "plot", "job_id"

    Returns
    -------
    collections.collections.namedtuple[numpy.ndarray]
        smoothed image: "smoothed_image"

    Raises
    ------
    ValueError
        when `filter_name` is not in {"avarage", "gaussian", "median", "bilateral"}
    TypeError
        when `image` does not have unsigned integer type
    '''
    input_dtype = image.dtype
    if not str(image.dtype).startswith('uint'):
        raise TypeError('Image must have unsigned integer type')

    if filter_name == 'average':
        smoothed_image = cv2.blur(
                                image, (filter_size, filter_size))
    elif filter_name == 'gaussian':
        smoothed_image = cv2.GaussianBlur(
                                image, (filter_size, filter_size), sigma)
    elif filter_name == 'gaussian-bilateral':
        smoothed_image = cv2.bilateralFilter(
                                image, filter_size, sigma_color, sigma_space)
    elif filter_name == 'median':
        # smoothed_image = cv2.medianBlur(image, filter_size)
        # TODO: the cv2 filter_name has some problems related to filter_size
        # consider mahotas (http://mahotas.readthedocs.org/en/latest/api.html?highlight=median#mahotas.median_filter)
        smoothed_image = median(image, disk(filter_size))
    elif filter_name == 'median-bilateral':
        smoothed_image = mean_bilateral(
                                image, disk(filter_size),
                                s0=sigma_space, s1=sigma_space)
    else:
        raise ValueError('Unknown filter_name. Implemented filters are:\n'
                         '"average", "gaussian", "median", and "bilateral"')

    if kwargs['plot']:

        rf = 4

        ds_img = block_reduce(image, (rf, rf), func=np.mean).astype(int)
        ds_smooth_img = block_reduce(smoothed_image, (rf, rf), func=np.mean).astype(int)

        # - keep image values at 16bit and adapt colorscale
        # - rescale both images the same for better comparison
        # - inverse y axis
        # - remove ticks and tick labels from axis (old issue with the
        #   assumption that 0, 0 is in the left lower corner)
        # - show only pixel values in case of hover event
        data = [
            plotly.graph_objs.Heatmap(
                z=ds_img,
                colorscale='Greys',
                hoverinfo='z',
                zauto=False,
                zmax=np.percentile(ds_img, 99.99),
                zmin=0,
                colorbar=dict(yanchor='bottom', y=0.55, len=0.45),
                y=np.linspace(image.shape[0], 0, ds_img.shape[0]),
                x=np.linspace(0, image.shape[1], ds_img.shape[1])
            ),
            plotly.graph_objs.Heatmap(
                z=ds_smooth_img,
                colorscale='Greys',
                hoverinfo='z',
                zmax=np.percentile(ds_img, 99.99),
                zmin=0,
                zauto=False,
                colorbar=dict(yanchor='top', y=0.45, len=0.45),
                y=np.linspace(image.shape[0], 0, ds_img.shape[0]),
                x=np.linspace(0, image.shape[1], ds_img.shape[1]),
                xaxis='x2',
                yaxis='y2'
            )
        ]

        layout = plotly.graph_objs.Layout(
            title='{name} smoothing filter of size {size}'.format(
                                    name=filter_name.capitalize(),
                                    size=filter_size),
            scene1=plotly.graph_objs.Scene(
                domain={'y': [0.55, 1.0]}
            ),
            scene2=plotly.graph_objs.Scene(
                domain={'y': [0.0, 0.45]}
            ),
            xaxis1=plotly.graph_objs.XAxis(
                ticks='',
                showticklabels=False
            ),
            yaxis1=plotly.graph_objs.YAxis(
                ticks='',
                showticklabels=False,
                domain=[0.55, 1.0]
            ),
            xaxis2=plotly.graph_objs.XAxis(
                ticks='',
                showticklabels=False,
                anchor='y2'
            ),
            yaxis2=plotly.graph_objs.YAxis(
                ticks='',
                showticklabels=False,
                domain=[0.0, 0.45],
            )
        )

        fig = plotly.graph_objs.Figure(data=data, layout=layout)

        plotting.save_plotly_figure(fig, kwargs['figure_file'])

    Output = collections.namedtuple('Output', 'smoothed_image')
    return Output(smoothed_image.astype(input_dtype))
