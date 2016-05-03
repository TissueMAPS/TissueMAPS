import logging
import image_registration
import imreg_dft as ird
import numpy as np

logger = logging.getLogger(__name__)


def calculate_shift(target_image, reference_image):
    '''Calculates the displacement between two images acquired at the same
    site in different cycles based on fast Fourier transform.

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
    transl, _, _ = ird.translation(target_image, reference_image)
    x = int(transl[1])
    y = int(transl[0])
    if y < 0:
        y -= 10
    if y > 0:
        y += 10
    x *= -1
    y *= -1
    # x, y, a, b = image_registration.chi2_shift(target_image, reference_image)
    # x = int(x)
    # y = int(y)
    # if x < 0:
    #     x -= 1
    # if y < 0:
    #     y -= 1
    return (y, x)


def calculate_overhang(y_shifts, x_shifts):
    '''Calculates the overhang of images acquired at the same site
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
    y_shifts = np.array(y_shifts)
    pos = y_shifts > 0
    if any(pos):
        bottom = np.max(y_shifts[pos])
    else:
        bottom = 0
    neg = y_shifts < 0
    if any(neg):
        top = np.abs(np.max(y_shifts[neg]))
    else:
        top = 0

    # in x direction
    x_shifts = np.array(x_shifts)
    pos = x_shifts > 0
    if any(pos):
        right = np.max(x_shifts[pos])
    else:
        right = 0
    neg = x_shifts < 0
    if any(neg):
        left = np.abs(np.max(x_shifts[neg]))
    else:
        left = 0

    return (top, bottom, right, left)
