'''Utility functions for common image processing routines.'''

import numpy as np
import logging
from skimage.exposure import rescale_intensity

logger = logging.getLogger(__name__)


def remove_border_objects(img):
    '''
    Given a matrix of a site image, set all pixels with
    ids belonging to border objects to zero.

    Parameters
    ----------
    img: numpy.ndarray[int32]
        labeled pixels array were objects (connected components) are encoded
        with unique integers

    Returns
    -------
    numpy.ndarray[int32]
        modified pixel array with values of border objects set to 0
    '''
    is_border_object = find_border_objects(img)
    mat = img.copy()  # Copy since we don't update in place
    mat[is_border_object] = 0
    return mat


def remove_objects(img, ids):
    '''
    Given a matrix of a site image, set all pixels whose values
    are in "ids" to zero.

    Parameters
    ----------
    img: numpy.ndarray[int32]
        labeled pixels array were objects (connected components) are encoded
        with unique integers
    ids: List[int]
        unique object ids

    Returns
    -------
    numpy.ndarray[int32]
        modified pixels array with pixel values in `ids` set to 0
    '''
    mat = img.copy()  # Copy since we don't update in place
    remove_ix = np.in1d(mat, ids).reshape(mat.shape)
    mat[remove_ix] = 0
    return mat


def compute_outlines(img, keep_ids=False):
    '''
    Given a labeled pixels array, return an array of the outlines of encoded
    objects.
    If `keep_ids` is True, the outlines will still consist of their cell's id,
    otherwise the outlines will be ``True`` and all other pixels ``False``.
    Note that in the case of keeping the ids,
    the output matrix will have the original bit depth!

    If a pixel is not zero and has at least one neighbor with a mat
    value, then it is part of the outline.

    Parameters
    ----------
    img: numpy.ndarray[int32]
        labeled pixels array were objects (connected components) are encoded
        with unique integers

    Note
    ----
    Code adapted from
    `CellProfiler <https://github.com/CellProfiler/CellProfiler/blob/master/cellprofiler/cpmath/outline.py>`_.
    '''
    lr_mat = img[1:, :] != img[:-1, :]
    ud_mat = img[:, 1:] != img[:, :-1]
    d1_mat = img[1:, 1:] != img[:-1, :-1]
    d2_mat = img[1:, :-1] != img[:-1, 1:]
    mat = np.zeros(img.shape, bool)
    mat[1:, :][lr_mat] = True
    mat[:-1, :][lr_mat] = True
    mat[:, 1:][ud_mat] = True
    mat[:, :-1][ud_mat] = True
    mat[1:, 1:][d1_mat] = True
    mat[:-1, :-1][d1_mat] = True
    mat[1:, :-1][d2_mat] = True
    mat[:-1, 1:][d2_mat] = True

    mat[0, :] = False
    mat[:, 0] = False
    mat[-1, :] = False
    mat[:, -1] = False

    if keep_ids:
        return mat * img
    else:
        output = np.zeros(img.shape, np.bool)
        output[mat] = True
        return output


def convert_to_uint8(img, min_value=None, max_value=None):
    '''
    Scale an image to 8-bit by linearly scaling from a given range
    to 0-255. The lower and upper values of the range can be set. If not set
    they default to the minimum and maximum intensity value of `img`.
    
    This can be useful for displaying an image in a figure, for example.

    Parameters
    ----------
    img: numpy.ndarray
        image that should be rescaled
    min_value: int, optional
        lower intensity value of rescaling range (default: `None`)
    max_value: int, optional
        upper intensity value of rescaling range (default: `None`)

    Returns
    -------
    numpy.ndarray[uint8]

    Note
    ----
    When no `min_value` or `max_value` is provided the result is equivalent to
    the corresponding method in ImageJ: Image > Type > 8-bit.
    '''
    if min_value is not None:
        if not isinstance(min_value, int):
            raise TypeError('Argument "min_value" must have type int.')
        min_value = min_value
    else:
        min_value = np.min(img)
    if max_value is not None:
        if not isinstance(max_value, int):
            raise TypeError('Argument "max_value" must have type int.')
        max_value = max_value
    else:
        max_value = np.max(img)
    in_range = (min_value, max_value)
    img_rescaled = rescale_intensity(
                    img, out_range='uint8', in_range=in_range).astype(np.uint8)
    return img_rescaled


def shift_and_crop(img, y, x, bottom, top, right, left, shift=True, crop=True):
    '''
    Shift and crop an image according to the calculated values shift and
    overhang values.

    Parameters
    ----------
    img: numpy.ndarray
        image that should be aligned
    y: int
        shift in y direction (positive value -> down, negative value -> up)
    x: int
        shift in x direction (position value -> right, negative value -> left)
    bottom: int
        pixels to crop at the bottom
    top: int
        pixels to crop at the top
    right: int
        pixels to crop at the right
    left: int
        pixels to crop at the left
    shift: bool, optional
        whether image should be shifted (default: ``True``) - if ``False``
        all pixel values are set to zero
    crop: bool, optional
        whether image should cropped or rather padded with zero valued pixels
        (default: ``True``)

    Returns
    -------
    numpy.array
        potentially shifted and cropped image

    Raises
    ------
    IndexError
        when shift or overhang values are too extreme
    '''
    try:
        if shift:
            row_start = top - y
            row_end = bottom + y
            if row_end == 0:
                row_end = img.shape[0]
            else:
                row_end = -row_end
            col_start = left - x
            col_end = right + x
            if col_end == 0:
                col_end = img.shape[1]
            else:
                col_end = -col_end
            if crop:
                aligned_im = img[row_start:row_end, col_start:col_end]
            else:
                aligned_im = np.zeros(img.shape, dtype=img.dtype)
                extracted_im = img[row_start:row_end, col_start:col_end]
                row_end = top + extracted_im.shape[0]
                col_end = left + extracted_im.shape[1]
                aligned_im[top:row_end, left:col_end] = extracted_im
        else:
            row_start = top
            if bottom == 0:
                row_end = img.shape[0]
            else:
                row_end = -bottom
            col_start = left
            if right == 0:
                col_end = img.shape[1]
            else:
                col_end = -right
            empty_im = np.zeros(img.shape, dtype=img.dtype)
            if crop:
                aligned_im = empty_im[row_start:row_end, col_start:col_end]
            else:
                aligned_im = empty_im
        return aligned_im
    except IndexError as e:
        raise IndexError('Shifting and cropping of the image failed!\n'
                         'Shift or overhang values are incorrect:\n%s'
                         % str(e))
    except Exception as e:
        raise Exception('Shifting and cropping of the image failed!\n'
                        'Reason: %s' % str(e))


def find_border_objects(img):
    '''
    Find the objects at the border of a labeled image.

    Parameters
    ----------
    img: numpy.ndarray[int32]
        labeled pixels array

    Returns
    -------
    List[bool]
        ``True`` if an object lies at the border of the `img` and
        ``False`` otherwise
    '''
    edges = [np.unique(img[0, :]),   # first row
             np.unique(img[-1, :]),  # last row
             np.unique(img[:, 0]),   # first col
             np.unique(img[:, -1])]  # last col

    # Count only unique ids and remove 0 since it signals 'empty space'
    border_ids = list(reduce(set.union, map(set, edges)).difference({0}))
    object_ids = np.unique(img[img != 0])
    return [True if o in border_ids else False for o in object_ids]


def correct_illumination(img, mean, std, log_transform=True):
    '''
    Correct fluorescence microscopy image for illumination artifacts.

    Parameters
    ----------
    img: numpy.ndarray[numpy.uint8 or numpy.uint16]
        image that should be corrected
    mean: numpy.ndarray[numpy.float64]
        matrix of mean values (same dimensions as `img`)
    std: numpy.ndarray[numpy.float64]
        matrix of standard deviation values (same dimensions as `img`)
    log_transform: bool, optional
        log10 transform `img` (default: ``True``)

    Returns
    -------
    numpy.ndarray
        corrected image (same data type as `img`)
    '''
    img_type = img.dtype

    # Do all computations with type float
    img = img.astype(np.float64)
    img[img == 0] = 1
    if log_transform:
        img = np.log10(img)
    img = (img - mean) / std
    img = (img * np.mean(std)) + np.mean(mean)
    if log_transform:
        img = 10 ** img

    # Convert back to original type.
    return img.astype(img_type)
