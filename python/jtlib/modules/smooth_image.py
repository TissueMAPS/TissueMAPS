import cv2
import skimage.morphology
import skimage.filters.rank
import skimage.measure
import collections
import numpy as np


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
        when `filter_name` is not in
        {"avarage", "gaussian", "median", "bilateral"}
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
        smoothed_image = skimage.filters.rank.median(
                                image, skimage.morphology.disk(filter_size))
    elif filter_name == 'median-bilateral':
        smoothed_image = skimage.filters.rank.mean_bilateral(
                                image, skimage.morphology.disk(filter_size),
                                s0=sigma_space, s1=sigma_space)
    else:
        raise ValueError('Unknown filter_name. Implemented filters are:\n'
                         '"average", "gaussian", "median", and "bilateral"')

    if kwargs['plot']:
        from .. import plotting

        clip_value = np.percentile(image, 99.99)
        data = [
            plotting.create_intensity_image_plot(
                        image, 'ul', clip_value=clip_value),
            plotting.create_intensity_image_plot(
                        smoothed_image, 'ur', clip_value=clip_value),
        ]

        fig = plotting.create_figure(
                    data,
                    title='''smoothed image with %s filter of size %s
                    ''' % (filter_name, filter_size)
        )
        plotting.save_figure(fig, kwargs['figure_file'])

    Output = collections.namedtuple('Output', 'smoothed_image')
    return Output(smoothed_image.astype(input_dtype))
