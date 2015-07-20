import cv2
import collections
import numpy as np
import pylab as plt
from jterator import jtapi


def smooth(InputImage, Filter, FilterSize, Sigma=0, SigmaColor=0, SigmaSpace=0,
           Adaptive=False, **kwargs):
    '''
    Jterator module for image smoothing.
    For more information see
    `opencv docs <http://opencv-python-tutroals.readthedocs.org/en/latest/py_tutorials/py_imgproc/py_filtering/py_filtering.html>`_.

    Parameters
    ----------
    InputImage: numpy.ndarray
        grayscale image that should be smoothed
    Filter: str
        filter kernel that should be applied: "avarage", "gaussian", "median"
        "bilateral" or "bilateral-adaptive"
    FilterSize: int
        size (width and height) of the kernel
    Sigma: int, optional
        standard deviation of the Gaussian kernel - only relevant for
        "gaussian" filter
    SigmaColor: int, optional
        Gaussian component (filter sigma) applied in the intensity domain
        (color space) - only relevant for "bilateral" filter
    SigmaSpace: int, optional
        Gaussian component (filter sigma) applied in the spacial domain
        (coordinate space) - only relevant for "bilateral" filter
    **kwargs: dict
        additional arguments provided by Jterator:
        "ProjectDir", "DataFile", "FigureFile", "Plot"

    Returns
    -------
    namedtuple[numpy.ndarray]
        smoothed image: "SmoothedImage"

    Raises
    ------
    ValueError
        when `Filter` is not in {"avarage", "gaussian", "median", "bilateral"}
    '''
    # TODO: choose better default values
    if Filter == 'average':
        img = cv2.blur(InputImage, (FilterSize, FilterSize))
    elif Filter == 'gaussian':
        img = cv2.GaussianBlur(InputImage, (FilterSize, FilterSize), Sigma)
    elif Filter == 'median':
        img = cv2.medianBlur(InputImage, FilterSize)
    elif Filter == 'bilateral':
        img = cv2.bilateralFilter(InputImage, FilterSize,
                                  SigmaColor, SigmaSpace)
    else:
        raise ValueError('Unknown filter. Available filters are:\n'
                         '"average", "gaussian", "median", and "bilateral"')

    if kwargs['Plot']:

        fig = plt.figure(figsize=(10, 10))
        ax1 = fig.add_subplot(1, 2, 1)
        ax2 = fig.add_subplot(1, 2, 2)

        ax1.imshow(InputImage, cmap='gray',
                   vmin=np.percentile(InputImage, 0.1),
                   vmax=np.percentile(InputImage, 99.9))
        ax1.set_title('InputImage', size=20)

        ax2.imshow(img, cmap='gray',
                   vmin=np.percentile(img, 0.1),
                   vmax=np.percentile(img, 99.9))
        ax2.set_title('SmoothedImage', size=20)

        fig.tight_layout()

        jtapi.savefigure(fig, kwargs['FigureFile'])

    output = collections.namedtuple('Output', 'SmoothedImage')
    return output(img)
