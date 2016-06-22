import cv2
import mahotas as mh
import skimage.morphology
import skimage.filters.rank
import skimage.measure
import numpy as np

VERSION = '0.0.1'


def main(image, filter_name, filter_size, sigma=0, sigma_color=0,
                 sigma_space=0, plot=False):
    '''Smoothes an image.

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
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    Dict[str, numpy.ndarray[numpy.int32] or str]
        * "smoothed_image": smoothed intensity image
        * "figure": html string in case `plot` is ``True``

    Raises
    ------
    ValueError
        when `filter_name` is not
        ``"avarage"``, ``"gaussian"``, ``"median"``, or ``"bilateral"``
    TypeError
        when `image` does not have unsigned integer type
    '''
    input_dtype = image.dtype
    if not str(image.dtype).startswith('uint'):
        raise TypeError('Image must have unsigned integer type.')

    if filter_name == 'average':
        smoothed_image = cv2.blur(
            image, (filter_size, filter_size)
        )
    elif filter_name == 'gaussian':
        smoothed_image = cv2.GaussianBlur(
            image, (filter_size, filter_size), sigma
        )
    elif filter_name == 'gaussian-bilateral':
        smoothed_image = cv2.bilateralFilter(
            image, filter_size, sigma_color, sigma_space
        )
    elif filter_name == 'median':
        # NOTE: the OpenCV median filter can't handle 16-bit images
        smoothed_image = mh.median_filter(
            image, np.ones((filter_size, filter_size), dtype=image.dtype)
        )
    elif filter_name == 'median-bilateral':
        smoothed_image = skimage.filters.rank.mean_bilateral(
            image, skimage.morphology.disk(filter_size),
            s0=sigma_space, s1=sigma_space
        )
    else:
        raise ValueError(
            'Unknown filter_name. Implemented filters are:\n'
            '"average", "gaussian", "median", and "bilateral"'
        )

    output = {'smoothed_image': smoothed_image.astype(input_dtype)}
    if plot:
        from jtlib import plotting

        clip_value = np.percentile(image, 99.99)
        data = [
            plotting.create_intensity_image_plot(
                        image, 'ul', clip_value=clip_value),
            plotting.create_intensity_image_plot(
                        smoothed_image, 'ur', clip_value=clip_value),
        ]

        output['figure'] = plotting.create_figure(
            data,
            title='image smoothed with {0} filter (kernel size: {1})'.format(
                filter_name, filter_size
            )
        )
    else:
        output['figure'] = str()

    return output
