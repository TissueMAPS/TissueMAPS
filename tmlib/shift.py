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


class ShiftDescription(object):
    '''
    Abstract base class for shift description for an image.

    A shift description consists of shift and overhang values as well as
    additional metainformation that are based on the registration of an
    image acquired at the same position with a corresponding image
    of the reference cycle.
    '''

    PERSISTENT = {
        'x_shift', 'y_shift', 'lower_overhang', 'upper_overhang',
        'left_overhang', 'right_overhang', 'omit', 'cycle', 'filename',
        'site'
    }

    def __init__(self, description=None):
        '''
        Initialize an instance of class ShiftDescription.

        Parameters
        ----------
        description: Dict[str, int or str or bool]
            shift description for an image acquisition site

        See also
        --------
        `tmlib.cfg`_
        '''
        self.description = description
        if self.description:
            self.set(self.description)

    @property
    def x_shift(self):
        '''
        Returns
        -------
        int
            shift of the image in pixels in x direction relative to its
            reference (positive value -> to the left; negative value -> to the
            right)
        '''
        return self._x_shift

    @x_shift.setter
    def x_shift(self, value):
        self._x_shift = value

    @property
    def y_shift(self):
        '''
        Returns
        -------
        int
            shift of the image in pixels in y direction relative to its
            reference (positive value -> downwards; negative value -> upwards)
        '''
        return self._y_shift

    @y_shift.setter
    def y_shift(self, value):
        self._y_shift = value

    @property
    def lower_overhang(self):
        '''
        Returns
        -------
        int
            overhang in pixels at the top side (bottom) of the image relative
            to its reference: pixels to crop at the top of the image
        '''
        return self._lower_overhang

    @lower_overhang.setter
    def lower_overhang(self, value):
        self._lower_overhang = value

    @property
    def upper_overhang(self):
        '''
        Returns
        -------
        int
            overhang in pixels at the bottom side (top) of the image relative
            to its reference: pixels to crop at the bottom of the image
        '''
        return self._upper_overhang

    @upper_overhang.setter
    def upper_overhang(self, value):
        self._upper_overhang = value

    @property
    def right_overhang(self):
        '''
        Returns
        -------
        int
            overhang in pixels at the left side of the image relative
            to its reference: pixels to crop at the right side of the image
        '''
        return self._right_overhang

    @right_overhang.setter
    def right_overhang(self, value):
        self._right_overhang = value

    @property
    def left_overhang(self):
        '''
        Returns
        -------
        int
            overhang in pixels at the right side of the image relative
            to its reference: pixels to crop at the left side of the image
        '''
        return self._left_overhang

    @left_overhang.setter
    def left_overhang(self, value):
        self._left_overhang = value

    @property
    def omit(self):
        '''
        Returns
        -------
        bool
            whether the image should not be shifted (``True`` means that the
            shift values for this site exceed the maximally tolerated shift)
        '''
        return self._omit

    @omit.setter
    def omit(self, value):
        self._omit = value

    @property
    def cycle(self):
        '''
        Returns
        -------
        str
            name of the corresponding cycle
        '''
        return self._cycle

    @cycle.setter
    def cycle(self, value):
        self._cycle = value

    @property
    def site(self):
        '''
        Returns
        -------
        int
            one-based site identifier number
        '''
        return self._site

    @site.setter
    def site(self, value):
        self._site = value

    @property
    def well(self):
        '''
        Returns
        -------
        str
            well identifier string, e.g. "A01"
        '''
        return self._well

    @well.setter
    def well(self, value):
        self._well = value

    @property
    def filename(self):
        '''
        Returns
        -------
        str
            name of the image file that was used for registration
        '''
        return self._filename

    @filename.setter
    def filename(self, value):
        self._filename = value

    def serialize(self):
        '''
        Serialize attributes to key-value pairs.

        Returns
        -------
        dict
            description as key-value pairs

        Raises
        ------
        AttributeError
            when instance doesn't have a required attribute
        '''
        serialized_description = dict()
        for a in dir(self):
            if a in ShiftDescription.PERSISTENT:
                serialized_description[a] = getattr(self, a)
        return serialized_description

    def set(self, description):
        '''
        Set attributes based on key-value pairs in dictionary.

        Parameters
        ----------
        description: dict
            description as key-value pairs

        Raises
        ------
        KeyError
            when keys for required attributes are not provided
        AttributeError
            when keys are provided that don't have a corresponding attribute
        '''
        missing_keys = [a for a in ShiftDescription.PERSISTENT
                        if a not in description.keys()]
        if len(missing_keys) > 0:
            raise KeyError('Missing keys: "%s"' % '", "'.join(missing_keys))
        for k, v in description.iteritems():
            if k not in ShiftDescription.PERSISTENT:
                raise AttributeError(
                        'Class "%s" has no attribute "%s"'
                        % (ShiftDescription.__class__.__name__, k))
            setattr(self, k, v)
