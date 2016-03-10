import logging
import mahotas as mh
import numpy as np

logger = logging.getLogger(__name__)


def threshold_image(image, correction_factor=1, min_threshold=None,
                    max_threshold=None,  plot=False):
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
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    dict
        outputs as key-value pairs:
            * "mask" (numpy.ndarray): thresholded mimage
            * "figure" (str, optional): html representation of the figure
              in case ``kwargs["plot"]`` is ``True``

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

    outputs = {'mask': thresh_image}

    if plot:
        from .. import plotting

        plots = [
            plotting.create_overlay_image_plot(image, thresh_image, 'ul'),
            plotting.create_mask_image_plot(thresh_image, 'ur'),
            [
                plotting.create_histogram_plot(image.flatten(), 'll'),
                plotting.create_line_plot(
                        [0, np.prod(image.shape)/100],
                        [corr_thresh, corr_thresh],
                        'll',
                        color=plotting.OBJECT_COLOR, line_width=4,
                    )
            ]
        ]

        outputs['figure'] = plotting.create_figure(
                        plots, plot_is_image=[True, True, False],
                        title='''thresholded image at pixel value %s
                        ''' % thresh
        )

    return outputs
