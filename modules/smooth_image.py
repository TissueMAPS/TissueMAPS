import cv2
from skimage.morphology import disk
from skimage.filters.rank import median
import collections
import numpy as np
import pylab as plt
from tmlib.jterator import jtapi


def smooth_image(input_image, filter, filter_size, sigma=0, sigma_color=0,
                 sigma_space=0, rescale_value=1, **kwargs):
    '''
    Jterator module for image smoothing.

    For more information on "average", "gaussian" and "bilateral" filters see
    `OpenCV tutorial <http://opencv-python-tutroals.readthedocs.org/en/latest/py_tutorials/py_imgproc/py_filtering/py_filtering.html>`_.

    For more information on "median" filter see
    `scikit-image docs <http://scikit-image.org/docs/dev/api/skimage.filters.html#median>`_.


    Parameters
    ----------
    input_image: numpy.ndarray
        grayscale image that should be smoothed
    filter: str
        filter kernel that should be applied: "avarage", "gaussian", "median"
        "bilateral" or "bilateral-adaptive"
    filter_size: int
        size (width and height) of the kernel (must be positive and odd)
    sigma: int, optional
        standard deviation of the Gaussian kernel - only relevant for
        "gaussian" filter
    sigma_color: int, optional
        Gaussian component (filter sigma) applied in the intensity domain
        (color space) - only relevant for "bilateral" filter
    sigma_space: int, optional
        Gaussian component (filter sigma) applied in the spacial domain
        (coordinate space) - only relevant for "bilateral" filter
    rescale_value: float, optional
        value by which `input_image` is multiplied before it's casted to
        unsigned integer type with depth 16 (e.g. if the image has dtype
        float64 with values between 0 and 1 you need to multiply it by 2^16)
    **kwargs: dict
        additional arguments provided by Jterator:
        "data_file", "figure_file", "experiment_dir", "plot", "job_id"

    Returns
    -------
    namedtuple[numpy.ndarray]
        smoothed image: "smoothed_image"

    Raises
    ------
    ValueError
        when `filter` is not in {"avarage", "gaussian", "median", "bilateral"}
    '''
    input_dtype = input_image.dtype
    if input_image.dtype != 'uint':
        print input_image
        input_image = np.array(input_image * rescale_value, dtype=np.uint16)
        print input_image

    if (input_image == 0).all():
        raise ValueError('All pixel values are 0. '
                         'Something went wrong during conversion to integer.\n'
                         'You may need to rescale the input image.')

    if filter == 'average':
        img = cv2.blur(input_image, (filter_size, filter_size))
    elif filter == 'gaussian':
        img = cv2.GaussianBlur(input_image, (filter_size, filter_size), sigma)
    elif filter == 'median':
        # img = cv2.medianBlur(input_image, filter_size)
        # TODO: the cv2 filter has some problems related to filter_size
        # consider mahotas (http://mahotas.readthedocs.org/en/latest/api.html?highlight=median#mahotas.median_filter)
        img = median(input_image, disk(filter_size))
    elif filter == 'bilateral':
        img = cv2.bilateralFilter(input_image, filter_size,
                                  sigma_color, sigma_space)
    else:
        raise ValueError('Unknown filter. Available filters are:\n'
                         '"average", "gaussian", "median", and "bilateral"')

    img = np.array(img / rescale_value, dtype=input_dtype)

    if kwargs['plot']:

        fig = plt.figure(figsize=(10, 10))
        ax1 = fig.add_subplot(1, 2, 1)
        ax2 = fig.add_subplot(1, 2, 2)

        ax1.imshow(input_image, cmap='gray',
                   vmin=np.percentile(input_image, 0.1),
                   vmax=np.percentile(input_image, 99.9))
        ax1.set_title('input image', size=20)

        ax2.imshow(img, cmap='gray',
                   vmin=np.percentile(img, 0.1),
                   vmax=np.percentile(img, 99.9))
        ax2.set_title('smoothed image', size=20)

        fig.tight_layout()

        jtapi.savefigure(fig, kwargs['figure_file'])

    output = collections.namedtuple('Output', 'smoothed_image')
    return output(img.astype(input_dtype))
