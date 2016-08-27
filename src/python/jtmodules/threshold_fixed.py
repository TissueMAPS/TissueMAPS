import logging
import mahotas as mh
import numpy as np

logger = logging.getLogger(__name__)

VERSION = '0.0.1'


def main(image, correction_factor=1, min_threshold=None, max_threshold=None,  plot=False):
    '''Thresholds an image with Otsu's method.
    For more information on the algorithmic implementation see
    :py:func:`mahotas.otsu`.

    Additional parameters allow correction of the calculated fixed threshold
    level or restriction of it to a defined range. This may be useful to prevent
    extreme levels in case the `image` contains artifacts.

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
    Dict[str, numpy.ndarray[bool] or str]
        * "mask": thresholded mimage
        * "figure": JSON string representation of the figure
    '''
    if max_threshold is None:
        max_threshold = np.max(image)
    logger.info('set maximal threshold: %d', max_threshold)

    if min_threshold is None:
        min_threshold = np.min(image)
    logger.info('set minimal threshold: %d', min_threshold)
    logger.info('set threshold correction factor: %.2f', correction_factor)

    thresh = mh.otsu(image)
    logger.info('calculated threshold level: %d', thresh)

    corr_thresh = thresh * correction_factor
    logger.info('corrected threshold level: %d', corr_thresh)

    if corr_thresh > max_threshold:
        corr_thresh = max_threshold
    elif corr_thresh < min_threshold:
        corr_thresh = min_threshold

    logger.info('threshold image at %d', corr_thresh)
    thresh_image = image > corr_thresh

    outputs = {'mask': thresh_image}

    if plot:
        logger.info('create plot')
        from jtlib import plotting
        outlines = mh.morph.dilate(mh.labeled.bwperim(thresh_image))
        plots = [
            plotting.create_intensity_overlay_image_plot(
                image, outlines, 'ul'
            ),
            plotting.create_mask_image_plot(thresh_image, 'ur')
        ]
        outputs['figure'] = plotting.create_figure(
            plots, title='thresholded at fixed level: %s' % thresh
        )
    else:
        outputs['figure'] = str()

    return outputs
