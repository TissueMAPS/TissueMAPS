import mahotas as mh
import collections
import numpy as np
import pylab as plt
# import matplotlib
from tmlib.jterator import jtapi
from tmlib import image_utils


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
        ax1 = fig.add_subplot(1, 2, 1)
        ax2 = fig.add_subplot(1, 2, 2)

        img_border = mh.labeled.borders(thresh_image)
        # matplotlib cannot handle uint16 images:
        # https://github.com/matplotlib/matplotlib/issues/2499
        # so let's rescale the image to 8-bit for display
        rescaled_image = image_utils.convert_to_uint8(image)
        img_overlay = mh.overlay(rescaled_image, img_border)
        ax1.imshow(img_overlay)
        ax1.set_title('overlay of outlines', size=20)

        # rescaled_image = image_utils.convert_to_uint8(image)
        # img_border = segment.compute_outlines_numpy(thresh_image)
        # img_mask = np.ma.array(rescaled_image, mask=~img_border)

        # figargs = {
        #     'interpolation': 'none',
        #     'vmin': rescaled_image.min(),
        #     'vmax': rescaled_image.max()
        # }
        # ax1.imshow(rescaled_image, cmap=plt.cm.Greys_r, **figargs)
        # ax1.imshow(img_mask, cmap=plt.cm.jet, **figargs)
        # ax1.set_title('mask trick', size=20)

        img_obj = np.zeros(thresh_image.shape)
        img_obj[thresh_image] = 1
        img_obj[~thresh_image] = np.nan

        ax2.imshow(img_obj, cmap=plt.cm.Set1)
        ax2.set_title('thresholded image', size=20)

        fig.tight_layout()

        jtapi.save_mpl_figure(fig, kwargs['figure_file'])

    output = collections.namedtuple('Output', 'thresholded_image')
    return output(thresh_image)
