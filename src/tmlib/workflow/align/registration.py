import os
import numpy as np
import logging
import image_registration
from tmlib.readers import DatasetReader

logger = logging.getLogger(__name__)


def calculate_shift(target_image, reference_image):
    '''
    Calculate displacement between two images based on fast Fourier transform.

    Parameters
    ----------
    target_image: numpy.ndarray
        image that should be registered
    reference_image: numpy.ndarray
        image that should be used as a reference

    Returns
    -------
    Tuple[int]
        shift in y and x direction
    '''
    x, y, a, b = image_registration.chi2_shift(target_image, reference_image)
    return (int(y), int(x))


def calculate_overhang(y_shifts, x_shifts):
    '''
    Calculates the overhang of images at one acquisition site
    across different acquisition cycles.

    Parameters
    ----------
    y_shifts: List[int]
        shifts along the y-axis
    x_shifts: List[int]
        shifts along the x-axis

    Returns
    -------
    List[int]
        upper, lower, right and left overhang
    '''
    # in y direction
    y_positive = [i > 0 for i in y_shifts]
    y_negetive = [i < 0 for i in y_shifts]
    if any(y_positive):  # down
        bottom = []
        for i in y_positive:
            bottom.append(y_shifts[i])
        bottom = max(bottom)
    else:
        bottom = 0

    if any(y_negetive):  # up
        top = []
        for i in y_negetive:
            top.append(y_shifts[i])
        top = abs(min(top))
    else:
        top = 0

    # in x direction
    x_positive = [i > 0 for i in x_shifts]
    x_negetive = [i < 0 for i in x_shifts]
    if any(x_positive):  # right
        right = []
        for i in x_positive:
            right.append(x_shifts[i])
        right = max(right)
    else:
        right = 0

    if any(x_negetive):  # left
        left = []
        for i in x_negetive:
            left.append(x_shifts[i])
        left = abs(min(left))
    else:
        left = 0

    return (top, bottom, right, left)
