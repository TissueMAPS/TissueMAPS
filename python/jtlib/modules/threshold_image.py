import logging
import mahotas as mh
import collections
import numpy as np
import skimage.measure

logger = logging.getLogger(__name__)


def threshold_image(image, correction_factor=1, min_threshold=None,
                    max_threshold=None,  **kwargs):
    '''
    Jterator module for thresholding an image with Otsu's method.
    For more information on the algorithmic implementation of the method see
    `mahotas docs <http://mahotas.readthedocs.org/en/latest/api.html?highlight=otsu#mahotas.otsu>`_.
    Additional parameters allow correction of the calculated threshold level
    or restriction of it to a defined range. This may be useful to prevent
    extreme levels when the `image` contains artifacts, for example.

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
    TypeError
        when `image` doesn't have unsigned integer type
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

    logger.info('threshold correction factor: %.2f', correction_factor)
    corr_thresh = thresh * correction_factor
    logger.info('final threshold level: %d', thresh)

    if corr_thresh > max_threshold:
        corr_thresh = max_threshold
    elif corr_thresh < min_threshold:
        corr_thresh = min_threshold

    thresh_image = image > corr_thresh

    if kwargs['plot']:
        import plotly
        from .. import plotting

        rf = 4
        # We add 1 to each pixel value to make sure that there are no zeros
        # in the image. This is exploited for overlaying the outlines of
        # segmented objects (see below).
        ds_img = skimage.measure.block_reduce(
                            image, (rf, rf), func=np.mean).astype(int) + 1
        ds_tresh_img = skimage.measure.block_reduce(
                            thresh_image, (rf, rf), func=np.mean).astype(int)

        # Keep pixels values with 16bit depth and adapt colorscale to 8bit
        clip_value = np.percentile(ds_img, 99.99)
        # Create an outline image for overlay of segmentation results
        outlines = skimage.measure.find_contours(
                            ds_tresh_img, 0.5, fully_connected='high')
        for coords in outlines:
            y = coords[:, 0].astype(int)
            x = coords[:, 1].astype(int)
            # Set outline pixel values to zero. We make sure that images
            # don't contain any zeros (see above).
            # This may not be case A nice side effect is that the outline color
            # will not be visible in the colorbar.
            ds_img[y, x] = 0

        colorscale = plotting.create_plotly_palette('Greys', clip_value)
        # Insert the color for the outlines into the colorscale. We insert it
        # at the end, but later reverse the scale for display, so zero values
        # in the image will be labeled with that color.
        colorscale[-1][1] = plotting.OBJECT_COLOR

        data = [
            plotly.graph_objs.Heatmap(
                z=ds_img,
                hoverinfo='z',
                colorscale=colorscale,
                reversescale=True,
                # Rescale pixel intensity values for display
                zmax=clip_value,
                zmin=0,
                zauto=False,
                colorbar=dict(
                    yanchor='bottom',
                    y=0.57,
                    x=0.43,
                    len=0.43),
                y=np.linspace(0, image.shape[0], ds_img.shape[0]),
                x=np.linspace(0, image.shape[1], ds_img.shape[1]),
                xaxis='x1',
                yaxis='y1'
            ),
            plotly.graph_objs.Heatmap(
                z=ds_tresh_img,
                hoverinfo='z',
                colorscale=[[0, 'rgb(0,0,0)'], [1, plotting.OBJECT_COLOR]],
                # colorbar=dict(yanchor='top', y=0.4, len=0.4),
                showscale=False,
                y=np.linspace(0, image.shape[0], ds_img.shape[0]),
                x=np.linspace(0, image.shape[1], ds_img.shape[1]),
                xaxis='x2',
                yaxis='y2'
            ),
            plotly.graph_objs.Histogram(
                x=ds_img.flatten(),
                marker=dict(
                    color='grey'
                ),
                showlegend=False,
                xaxis='x3',
                yaxis='y3'
            ),
            plotly.graph_objs.Scatter(
                y=[0, np.prod(ds_img.shape)/50],
                x=[corr_thresh, corr_thresh],
                marker=dict(
                    size=1
                ),
                line=dict(
                    color=plotting.OBJECT_COLOR,
                    width=4
                ),
                showlegend=False,
                xaxis='x3',
                yaxis='y3'
            )
        ]

        layout = plotly.graph_objs.Layout(
            title='Pixels with intensity values above {level}'.format(
                        level=corr_thresh),
            xaxis1=dict(
                domain=[0, 0.43],
                anchor='y1'
            ),
            yaxis1=dict(
                domain=[0.57, 1],
                anchor='x1',
                autorange='reversed'
            ),
            xaxis2=dict(
                domain=[0.57, 1],
                anchor='y2'
            ),
            yaxis2=dict(
                ticks='', showticklabels=False,
                domain=[0.57, 1],
                anchor='x2',
                autorange='reversed'
            ),
            xaxis3=dict(
                domain=[0, 0.43],
                anchor='y3'
            ),
            yaxis3=dict(
                domain=[0, 0.43],
                anchor='x3'
            )
        )

        fig = plotly.graph_objs.Figure(data=data, layout=layout)
        plotting.save_plotly_figure(fig, kwargs['figure_file'])

    Output = collections.namedtuple('Output', 'thresholded_image')
    return Output(thresh_image)
