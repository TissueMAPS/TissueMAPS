'''Utility functions for common image processing routines.'''

import numpy as np
import logging

logger = logging.getLogger(__name__)


def remove_border_objects(img):
    '''Given a matrix of a site image, set all pixels with
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
    '''Given a matrix of a site image, set all pixels whose values
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
    '''Given a labeled pixels array, return an array of the outlines of encoded
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


# def convert_to_uint8(img, min_value=None, max_value=None):
#     '''
#     Scale an image to 8-bit by linearly scaling from a given range
#     to 0-255. The lower and upper values of the range can be set. If not set
#     they default to the minimum and maximum intensity value of `img`.
    
#     This can be useful for displaying an image in a figure, for example.

#     Parameters
#     ----------
#     img: numpy.ndarray
#         image that should be rescaled
#     min_value: int, optional
#         lower intensity value of rescaling range (default: `None`)
#     max_value: int, optional
#         upper intensity value of rescaling range (default: `None`)

#     Returns
#     -------
#     numpy.ndarray[uint8]

#     Note
#     ----
#     When no `min_value` or `max_value` is provided the result is equivalent to
#     the corresponding method in ImageJ: Image > Type > 8-bit.
#     '''
#     if min_value is not None:
#         if not isinstance(min_value, int):
#             raise TypeError('Argument "min_value" must have type int.')
#         min_value = min_value
#     else:
#         min_value = np.min(img)
#     if max_value is not None:
#         if not isinstance(max_value, int):
#             raise TypeError('Argument "max_value" must have type int.')
#         max_value = max_value
#     else:
#         max_value = np.max(img)
#     in_range = (min_value, max_value)
#     img_rescaled = rescale_intensity(
#                     img, out_range='uint8', in_range=in_range).astype(np.uint8)
#     return img_rescaled


def map_to_uint8(img, lower_bound=None, upper_bound=None):
    '''Maps a 16-bit image trough a lookup table to convert it to 8-bit.
    
    Parameters
    ----------
    img: numpy.ndarray[np.uint16]
        image that should be mapped
    lower_bound: int, optional
        lower bound of the range that should be mapped to ``[0, 255]``,
        value must be in the range ``[0, 65535]``
        (defaults to ``numpy.min(img)``)
    upper_bound: int, optional
        upper bound of the range that should be mapped to ``[0, 255]``,
        value must be in the range ``[0, 65535]``
        (defaults to ``numpy.max(img)``)
    
    Returns
    -------
    numpy.ndarray[uint8]
        mapped image
    '''
    if img.dtype != np.uint16:
        raise TypeError('"img" must have 16-bit unsigned integer type.')
    if not(0 <= lower_bound < 2**16) and lower_bound is not None:
            raise ValueError('"lower_bound" must be in the range [0, 65535]')
    if not(0 <= upper_bound < 2**16) and upper_bound is not None:
        raise ValueError('"upper_bound" must be in the range [0, 65535]')
    if lower_bound is None:
        lower_bound = np.min(img)
    if upper_bound is None:
        upper_bound = np.max(img)
    if lower_bound >= upper_bound:
        raise ValueError('"lower_bound" must be smaller than "upper_bound"')
    lut = np.concatenate([
        np.zeros(lower_bound, dtype=np.uint16),
        np.linspace(0, 255, upper_bound - lower_bound).astype(np.uint16),
        np.ones(2**16 - upper_bound, dtype=np.uint16) * 255
    ])
    return lut[img].astype(np.uint8)


def mip(zplanes):
    '''Performs maximum intensity projection.

    Parameters
    ----------
    zplanes: List[numpy.ndarray[numpy.uint16]]
        2D pixel planes acquired at different z resolution levels

    Returns
    -------
    numpy.ndarray[numpy.uint16]
        projected image

    Note
    ----
    It's assumed that all `zplanes` have same data type and dimensions.
    '''
    dims = zplanes[0].shape
    dtype = zplanes[0].dtype
    stack = np.zeros((len(zplanes), dims[0], dims[1]), dtype=dtype)
    for z in xrange(len(zplanes)):
        stack[z, :, :] = zplanes[z]
    return np.max(stack, axis=0)


def shift_and_crop(img, y, x, bottom, top, right, left, crop=True):
    '''Shifts and crops an image according to the calculated values shift and
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
        row_start = top - y
        if row_start <= 0:
            row_start = 0
        row_end = bottom + y
        if row_end <= 0:
            row_end = img.shape[0]
        else:
            row_end = -row_end
        col_start = left - x
        if col_start <= 0:
            col_start = 0
        col_end = right + x
        if col_end <= 0:
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
        return aligned_im
    except IndexError as e:
        raise IndexError(
            'Shifting and cropping of the image failed!\n'
            'Shift or overhang values are incorrect:\n%s' % str(e)
        )
    except Exception as e:
        raise Exception(
            'Shifting and cropping of the image failed!\n'
            'Reason: %s' % str(e)
        )


def find_border_objects(img):
    '''Finds the objects at the border of a labeled image.

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
    '''Corrects fluorescence microscopy image for illumination artifacts.

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
