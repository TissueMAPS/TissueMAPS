# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import logging
import image_registration
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
    logger.debug('calculate shift between target and reference image')
    x, y, a, b = image_registration.chi2_shift(target_image, reference_image)
    return (int(np.round(y)), int(np.round(x)))


def calculate_overlap(y_shifts, x_shifts):
    '''Calculates the overlap of images acquired at the same site
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
        number of overhanging pixels at the top, bottom, right and left side
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
        top = np.abs(np.min(y_shifts[neg]))
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
        left = np.abs(np.min(x_shifts[neg]))
    else:
        left = 0

    return (top, bottom, right, left)
