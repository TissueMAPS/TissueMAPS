import logging
import mahotas as mh
import cv2
import numpy as np

logger = logging.getLogger(__name__)

VERSION = '0.0.1'


def main(image, kernel_size, fill=True, plot=False):
    '''Thresholds an image using an adaptive method, where different thresholds
    get applied to different regions of the image.
    For more information on the algorithmic implementation see
    :py:func:`cv2.adaptiveThreshold`.

    Additional parameters allow correction of the calculated fixed threshold
    level or restriction of it to a defined range. This may be useful to prevent
    extreme levels in case the `image` contains artifacts.

    Parameters
    ----------
    image: numpy.ndarray
        grayscale image that should be thresholded
    kernel_size: int
        size of the neighbourhood region that's used to calculate the threshold
        value at each pixel position (must be an odd number)
    fill: bool, optional
        whether holes in connected components should be filled
        (default: ``True``)
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    Dict[str, numpy.ndarray[bool] or str]
        * "mask": thresholded mimage
        * "figure": JSON string representation of the figure

    Raises
    ------
    ValueError
        when `kernel_size` is not an odd number
    '''
    if kernel_size % 2 == 0:
        raise ValueError('Argument "kernel_size" must be an odd integer.')
    logger.debug('set kernel size: %d', kernel_size)

    logger.debug('map image intensities to 8-bit range')
    image_8bit = mh.stretch(image)

    logger.info('threshold image')
    thresh_image = cv2.adaptiveThreshold(
        image_8bit, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,
        kernel_size, 0
    )
    thresh_image = thresh_image > 0

    if fill:
        logger.info('fill holes')
        thresh_image = mh.close_holes(thresh_image)
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
            plots,
            title='thresholded adaptively with kernel size: %d' % kernel_size
        )
    else:
        outputs['figure'] = str()

    return outputs

