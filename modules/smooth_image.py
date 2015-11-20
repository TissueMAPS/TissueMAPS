import cv2
from skimage.morphology import disk
from skimage.filters.rank import median
import collections
import numpy as np
import matplotlib.pyplot as plt
from jtlib import plotting


def smooth_image(image, filter, filter_size, sigma=0, sigma_color=0,
                 sigma_space=0, **kwargs):
    '''
    Jterator module for smoothing an image.

    For more information on "average", "gaussian" and "bilateral" filters see
    `OpenCV tutorial <http://opencv-python-tutroals.readthedocs.org/en/latest/py_tutorials/py_imgproc/py_filtering/py_filtering.html>`_.

    For more information on "median" filter see
    `scikit-image docs <http://scikit-image.org/docs/dev/api/skimage.filters.html#median>`_.


    Parameters
    ----------
    image: numpy.ndarray
        grayscale image that should be smoothed
    filter: str
        filter kernel that should be applied: "avarage", "gaussian", "median"
        "bilateral" or "bilateral-adaptive"
    filter_size: int
        size (width/height) of the kernel (must be positive and odd)
    sigma: int, optional
        standard deviation of the Gaussian kernel - only relevant for
        "gaussian" filter (default: ``0``)
    sigma_color: int, optional
        Gaussian component (filter sigma) applied in the intensity domain
        (color space) - only relevant for "bilateral" filter (default: ``0``)
    sigma_space: int, optional
        Gaussian component (filter sigma) applied in the spacial domain
        (coordinate space) - only relevant for "bilateral" filter
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
        when `filter` is not in {"avarage", "gaussian", "median", "bilateral"}
    TypeError
        when `image` does not have unsigned integer type
    '''
    input_dtype = image.dtype
    if not str(image.dtype).startswith('uint'):
        raise TypeError('Image must have unsigned integer type')

    if filter == 'average':
        img = cv2.blur(image, (filter_size, filter_size))
    elif filter == 'gaussian':
        img = cv2.GaussianBlur(image, (filter_size, filter_size), sigma)
    elif filter == 'median':
        # img = cv2.medianBlur(image, filter_size)
        # TODO: the cv2 filter has some problems related to filter_size
        # consider mahotas (http://mahotas.readthedocs.org/en/latest/api.html?highlight=median#mahotas.median_filter)
        img = median(image, disk(filter_size))
    elif filter == 'bilateral':
        img = cv2.bilateralFilter(image, filter_size, sigma_color, sigma_space)
    else:
        raise ValueError('Unknown filter. Implemented filters are:\n'
                         '"average", "gaussian", "median", and "bilateral"')

    if kwargs['plot']:

        fig = plt.figure()
        ax1 = fig.add_subplot(1, 2, 1)
        ax2 = fig.add_subplot(1, 2, 2)

        ax1.imshow(image, cmap='gray',
                   vmin=np.percentile(image, 0.1),
                   vmax=np.percentile(image, 99.9))
        ax1.set_title('input image', size=20)

        ax2.imshow(img, cmap='gray',
                   vmin=np.percentile(img, 0.1),
                   vmax=np.percentile(img, 99.9))
        ax2.set_title('smoothed image', size=20)

        fig.tight_layout()

        plotting.save_mpl_figure(fig, kwargs['figure_file'])

    output = collections.namedtuple('Output', 'smoothed_image')
    return output(img.astype(input_dtype))
