import logging
import mahotas as mh
import plotly
import colorlover as cl
import collections
import numpy as np
import skimage.measure
from jtlib import plotting

logger = logging.getLogger(__name__)


def threshold_image(image, correction_factor=1, min_threshold=None,
                    max_threshold=None,  **kwargs):
    '''
    Jterator module for thresholding an image with Otsu's method.
    For more information see
    `mahotas docs <http://mahotas.readthedocs.org/en/latest/api.html?highlight=otsu#mahotas.otsu>`_.

    Parameters
    ----------
    image: numpy.ndarray
        grayscale image that should be thresholded
    correction_factor: int, optional
        value by which the calculated threshold level will be multiplied
        (default: ``1``)
    min_threshold: int, optional
        minimal threshold level (default: ``numpy.min(image)``)
    max_threshold: int, optional
        maximal threshold level (default: ``numpy.max(image)``)
    **kwargs: dict
        additional arguments provided by Jterator:
        "data_file", "figure_file", "experiment_dir", "plot", "job_id"

    Returns
    -------
    collections.namedtuple[numpy.ndarray[bool]]
        binary thresholded image: "thresholded_image"

    Raises
    ------
    ValueError
        when all pixel values of `image` are zero after rescaling
    '''
    if max_threshold is None:
        max_threshold = np.max(image)
    logger.info('set maximal threshold: %d', max_threshold)

    if min_threshold is None:
        min_threshold = np.min(image)
    logger.info('set minimal threshold: %d', min_threshold)

    # threshold function requires unsigned integer type
    if not str(image.dtype).startswith('uint'):
        raise TypeError('Image must have unsigned integer type')

    thresh = mh.otsu(image)
    logger.info('calculated threshold level: %d', thresh)

    logger.info('threshold correction factor: %d', correction_factor)
    thresh = thresh * correction_factor
    logger.info('final threshold level: %d', thresh)

    if thresh > max_threshold:
        thresh = max_threshold
    elif thresh < min_threshold:
        thresh = min_threshold

    thresh_image = image > thresh

    if kwargs['plot']:

        rf = 4
        ds_img = skimage.measure.block_reduce(
                            image, (rf, rf), func=np.mean).astype(int)
        ds_tresh_img = skimage.measure.block_reduce(
                            thresh_image, (rf, rf), func=np.mean).astype(int)

        # - keep image values at 16bit and adapt colorscale
        # - inverse y axis
        # - remove ticks and tick labels from axis (old issue with the
        #   assumption that 0, 0 is in the left lower corner)
        # - show only pixel values in case of hover event
        colors = cl.scales['3']['div']['RdGy']
        data = [
            plotly.graph_objs.Heatmap(
                z=ds_img,
                hoverinfo='z',
                colorscale='Greys',
                zmax=np.percentile(ds_img, 99.99),
                zmin=0,
                zauto=False,
                colorbar=dict(yanchor='bottom', y=0.55, len=0.45),
                y=np.linspace(image.shape[0], 0, ds_img.shape[0]),
                x=np.linspace(0, image.shape[1], ds_img.shape[1])
            ),
            plotly.graph_objs.Heatmap(
                z=ds_tresh_img,
                hoverinfo='z',
                # colorscale='Hot',
                colorscale=colors,
                colorbar=dict(
                    yanchor='top', y=0.45, len=0.45, tickvals=[0, 1]
                ),
                showscale=False,
                y=np.linspace(image.shape[0], 0, ds_img.shape[0]),
                x=np.linspace(0, image.shape[1], ds_img.shape[1]),
                xaxis='x2',
                yaxis='y2'
            )
        ]

        layout = plotly.graph_objs.Layout(
            title='Threshold: %d' % thresh,
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

    Output = collections.namedtuple('Output', 'thresholded_image')
    return Output(thresh_image)
