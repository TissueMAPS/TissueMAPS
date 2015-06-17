import numpy as np
from scipy import misc
from image_registration import chi2_shift


def calculate_shift(filename, ref_filename):
    '''
    Calculate shift between two images from different cycles.

    Input:
        :filename:          absolute path to image that should be registered

        :ref_filename:      absolute path to image that should be used as
                            a reference for registration

    Output:
        :x:                 shift in x direction (integer)
        :y:                 shift in y direction (integer)


    "Apparently astronomical images look a lot like microscopic images." [*]

    [*] http://image-registration.readthedocs.org/en/latest/
    '''
    # Load image that should be registered
    im = np.array(misc.imread(filename), dtype='float64')
    # Load reference image
    ref_im = np.array(misc.imread(ref_filename), dtype='float64')
    # Calculate shift between images
    (x, y, a, b) = chi2_shift(im, ref_im)
    return [x, y]


def calculate_overlap(x_shift, y_shift):
    '''
    Calculates the overlap of images from different
    acquisition cycles based on pre-calculated shift vectors.

    Input:
        :x_shift:       list of shift values in x direction
        :y_shift:       list of shift values in y direction

    Output:
        :top:           upper overlap    
        :bottom:        lower overlap
        :right:         right overlap
        :left:          left overlap
    '''

    # in y direction
    y_positive = [i > 0 for i in y_shift]
    y_negetive = [i < 0 for i in y_shift]
    if any(y_positive):  # down
        bottom = []
        for i in y_positive:
            bottom.append(y_shift[i])
        bottom = max(bottom)
    else:
        bottom = 0

    if any(y_negetive):  # up
        top = []
        for i in y_negetive:
            top.append(y_shift[i])
        top = abs(min(top))
    else:
        top = 0

    # in x direction
    x_positive = [i > 0 for i in x_shift]
    x_negetive = [i < 0 for i in x_shift]
    if any(x_positive):  # right
        right = []
        for i in x_positive:
            right.append(x_shift[i])
        right = max(right)
    else:
        right = 0

    if any(x_negetive):  # left
        left = []
        for i in x_negetive:
            left.append(x_shift[i])
        left = abs(min(left))
    else:
        left = 0

    return(top, bottom, right, left)
