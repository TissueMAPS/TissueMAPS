import operator as op
from gi.repository import Vips
import numpy as np
import logging
from .. import image_utils

logger = logging.getLogger(__name__)


def remove_border_objects_numpy(im):
    '''
    Given a matrix of a site image, set all pixels with
    ids belonging to border objects to zero.

    Parameters
    ----------
    im: numpy.ndarray
        image matrix with values corresponding to object ids

    Returns
    -------
    numpy.ndarray
        modified image matrix with pixel values of border objects set to 0
    '''
    is_border_object = image_utils.find_border_objects(im)
    mat = im.copy()
    mat[is_border_object] = 0
    return mat


def remove_border_objects_vips(im, is_source_uint16=True):
    '''
    Given a matrix of a site image, set all pixels with
    ids belonging to border objects to zero.

    Parameters
    ----------
    im: Vips.Image
        image matrix with values corresponding to object ids
    is_source_uint16: bool, optional
        indicating if the source band format is uin16 (defaults to uint8)

    Returns
    ------- 
    Vips.Image
        modified image matrix with pixel values of border objects set to 0
    '''
    # Extract the edges on each side of the image
    left = im.extract_area(0, 0, 1, im.height)
    right = im.extract_area(im.width-1, 0, 1, im.height)
    top = im.extract_area(0, 0, im.width, 1)
    bottom = im.extract_area(0, im.height-1, im.width, 1)

    for border in [left, right, top, bottom]:
        # Create a histogram, i.e. a 1 x 2^16
        hist = border.hist_find()
        id_lut = Vips.Image.identity(ushort=is_source_uint16)
        is_nonzero = hist > 0
        lut = Vips.Image.ifthenelse(is_nonzero, 0, id_lut)
        im = im.maplut(lut)

    return im


def remove_objects_numpy(im, ids):
    '''
    Given a matrix of a site image, set all pixels whose values
    are in "ids" to zero.

    Parameters
    ----------
    im: numpy.ndarray
        image matrix with values corresponding to object ids
    ids: List[int]
        unique object ids

    Returns
    -------
    numpy.ndarray
        modified image matrix with pixel values in `ids` set to 0
    '''
    mat = im.copy()  # Copy since we don't update in place
    remove_ix = np.in1d(mat, ids).reshape(mat.shape)
    mat[remove_ix] = 0
    return mat


def remove_objects_vips(im, ids, is_source_uint16=True):
    '''
    Given a matrix of a site image, set all pixels whose values
    are in "ids" to zero.

    Parameters
    ----------
    im: Vips.Image
        image matrix with values corresponding to object ids
    ids: List[int]
        unique object ids
    is_source_uint16: bool, optional
        indicating if the source band format is uin16 (defaults to uint8)

    Returns
    -------
    Vips.Image
        modified image matrix with pixel values in ids set to 0
    '''
    id_lut = Vips.Image.identity(ushort=is_source_uint16)
    for i in ids:
        id_lut = (id_lut == i).ifthenelse(0, id_lut)
    im = im.maplut(id_lut)
    return im


def compute_outlines_numpy(labels, keep_ids=False):
    '''
    Given a label matrix, return a matrix of the outlines of labeled objects.
    If `keep_ids` is True, the outlines will still consist of their cell's id,
    otherwise the outlines will be ``True`` and all other pixels ``False``.
    Note that in the case of keeping the ids,
    the output matrix will have the original bit depth!

    If a pixel is not zero and has at least one neighbor with a different
    value, then it is part of the outline.

    Taken from the BSD-licensed file:
    https://github.com/CellProfiler/CellProfiler/blob/master/cellprofiler/cpmath/outline.py
    '''
    lr_different = labels[1:, :] != labels[:-1, :]
    ud_different = labels[:, 1:] != labels[:, :-1]
    d1_different = labels[1:, 1:] != labels[:-1, :-1]
    d2_different = labels[1:, :-1] != labels[:-1, 1:]
    different = np.zeros(labels.shape, bool)
    different[1:, :][lr_different] = True
    different[:-1, :][lr_different] = True
    different[:, 1:][ud_different] = True
    different[:, :-1][ud_different] = True
    different[1:, 1:][d1_different] = True
    different[:-1, :-1][d1_different] = True
    different[1:, :-1][d2_different] = True
    different[:-1, 1:][d2_different] = True

    different[0, :] = False
    different[:, 0] = False
    different[-1, :] = False
    different[:, -1] = False

    if keep_ids:
        return different * labels
    else:
        output = np.zeros(labels.shape, np.bool)
        output[different] = True
        return output


def compute_outlines_vips(im):
    '''
    Given a label matrix, return a matrix of the outlines of labeled objects.

    If a pixel is not zero and has at least one neighbor with a different
    value, then it is part of the outline.

    For more info about how this works, see
    `libvips-morphology <http://www.vips.ecs.soton.ac.uk/supported/current/doc/html/libvips/libvips-morphology.html>`_
    '''
    # Since the images are sometimes not square, they can't be rotated at all times.
    # Normally you would define one mask and apply it repeatedly to the image while rotating it.
    # Since this isn't possible, I just define all the masks right here.
    # 0 means: 'match a background pixel'
    # 255 means: 'match an object pixel (nonzero pixel)
    # 128 means: 'match any pixel'
    # Note that VIPS uses 255 for TRUE and 0 for FALSE.

    masks = [
        [[0   , 128 , 128]  ,
         [128 , 255 , 128]  ,
         [128 , 255 , 128]] ,
        [[128 , 0   , 128]  ,
         [128 , 255 , 128]  ,
         [128 , 255 , 128]] ,
        [[128 , 128 , 0]    ,
         [0   , 255 , 128]  ,
         [128 , 255 , 128]] ,
        [[0   , 128 , 128]  ,
         [128 , 255 , 255]  ,
         [128 , 128 , 128]] ,
        [[128 , 128 , 128]  ,
         [0   , 255 , 255]  ,
         [128 , 128 , 128]] ,
        [[128 , 128 , 128]  ,
         [128 , 255 , 255]  ,
         [0   , 128 , 128]] ,
        [[128 , 255 , 128]  ,
         [128 , 255 , 128]  ,
         [0   , 128 , 128]] ,
        [[128 , 255 , 128]  ,
         [128 , 255 , 128]  ,
         [128 , 0   , 128]] ,
        [[128 , 255 , 128]  ,
         [128 , 255 , 128]  ,
         [128 , 128 , 0]]   ,
        [[128 , 128 , 128]  ,
         [255 , 255 , 128]  ,
         [128 , 128 , 0]]   ,
        [[128 , 128 , 128]  ,
         [255 , 255 , 0]    ,
         [128 , 128 , 128]] ,
        [[128 , 128 , 0]    ,
         [255 , 255 , 128]  ,
         [128 , 128 , 128]]
    ]

    results = []
    nonbg = im > 0  # how can we preserve ids?
    # Apply all the masks and save each result
    for i, mask in enumerate(masks):
        img = nonbg.morph(mask, 'erode')
        results.append(img)

    # Combine all the images
    images_disj = reduce(op.or_, results)
    return images_disj
