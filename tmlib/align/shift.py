import numpy as np
import logging
from gi.repository import Vips

logger = logging.getLogger(__name__)


def shift_and_crop_numpy(im, y, x, bottom, top, right, left,
                         shift=True, crop=True):
    '''
    Shift and crop an image according to the calculated values shift and
    overhang values.

    Parameters
    ----------
    im: numpy.ndarray or Vips.Image
        input image
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
        it is still cropped, but all pixel values are set to zero
    crop: bool, optional
        whether images should cropped or rather padded with zero valued pixels
        (default: ``True``)

    Returns
    -------
    numpy.array
        shifted and cropped image

    Raises
    ------
    IndexError
        when shift or overhang values are too extreme
    Exception
        when it fails for unknown reasons
    '''
    try:
        if shift:
            if crop:
                aligned_im = im[(top-y):-(bottom+y+1), (left-x):-(right+x+1)]
            else:
                aligned_im = np.zeros(im.shape, dtype=im.dtype)
                aligned_im[im[(top-y):-(bottom+y+1), (left-x):-(right+x+1)]] = \
                    im[(top-y):-(bottom+y+1), (left-x):-(right+x+1)]
        else:
            empty_im = np.zeros(im.shape, dtype=im.dtype)
            if crop:
                aligned_im = empty_im[top:-(bottom+1), left:-(right+1)]
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


def shift_and_crop_vips(im, y, x, bottom, top, right, left,
                        shift=True, crop=True):
    '''
    Shift and crop an image according to the calculated values shift and
    overhang values.

    Parameters
    ----------
    im: Vips.Image
        input image
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
        it is still cropped, but all pixel values are set to zero
    crop: bool, optional
        whether images should cropped or rather padded
        with zero valued pixels (default: ``True``)

    Returns
    -------
    Vips.Image
        shifted and cropped image

    Raises
    ------
    IndexError
        when shift or overhang values are too extreme
    Exception
        when it fails for unknown reasons
    '''
    empty_im = Vips.Image.black(
                    im.width, im.height, bands=im.bands).cast(im.get_format())
    try:
        if shift:
            offset_left = left-x
            offset_top = top-y
            width = im.width-right-left
            height = im.height-bottom-top
            if crop:
                aligned_im = im.crop(
                                offset_left, offset_top, width, height)
            else:
                extracted_im = im.crop(
                                offset_left, offset_top, width, height)
                aligned_im = empty_im.insert(
                                extracted_im, left, top)
        else:
            offset_left = left
            offset_top = top
            width = im.width-right-left
            height = im.height-bottom-top
            if crop:
                aligned_im = empty_im.crop(
                                offset_left, offset_top, width, height)
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
