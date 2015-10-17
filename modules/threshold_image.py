import mahotas as mh
import collections
import numpy as np
import pylab as plt
from skimage.exposure import rescale_intensity
from tmlib.jterator import jtapi


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
    namedtuple[numpy.ndarray[bool]]
        binary thresholded image: "thresholded_image"

    Raises
    ------
    ValueError
        when all pixel values of `image` are zero after rescaling
    '''
    if max_threshold is None:
        max_threshold = np.max(image)
    if min_threshold is None:
        min_threshold = np.min(image)

    # threshold function requires unsigned integer type
    if not str(image.dtype).startswith('uint'):
        raise TypeError('Image must have unsigned integer type')

    thresh = mh.otsu(image)

    thresh = thresh * correction_factor

    if thresh > max_threshold:
        thresh = max_threshold
    elif thresh < min_threshold:
        thresh = min_threshold

    thresh_image = image > thresh

    if kwargs['plot']:

        fig = plt.figure(figsize=(10, 10))
        ax1 = fig.add_subplot(2, 2, 1)
        ax2 = fig.add_subplot(2, 2, 2)
        ax3 = fig.add_subplot(2, 2, 4)

        ax1.imshow(image, cmap='gray',
                   vmin=np.percentile(image, 0.1),
                   vmax=np.percentile(image, 99.9))
        ax1.set_title('input image', size=20)

        ax2.imshow(thresh_image)
        ax2.set_title('thresholded image', size=20)

        img_border = mh.labeled.borders(thresh_image)
        # matplotlib cannot handle uint16 images:
        # https://github.com/matplotlib/matplotlib/issues/2499
        # so let's rescale the image to 8-bit for display
        rescaled_image = rescale_intensity(image,
                                           out_range='uint8').astype(np.uint8)
        img_overlay = mh.overlay(rescaled_image, img_border)
        ax3.imshow(img_overlay)
        ax3.set_title('Overlay', size=20)

        fig.tight_layout()

        jtapi.savefigure(fig, kwargs['figure_file'])

    output = collections.namedtuple('Output', 'thresholded_image')
    return output(thresh_image)
