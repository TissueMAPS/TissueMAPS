import numpy as np
from gi.repository import Vips


def shift_and_crop_numpy(im, y, x, upper, lower, left, right, shift=True):
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
    upper: int
        upper overhang - pixels cropped at the bottom
    lower: int
        lower overhang - pixels cropped at the top
    left: int
        left overhang - pixels cropped at the right
    right: int
        right overhang - pixels cropped at the left
    shift: bool, optional
        whether image should be shifted (if ``False`` it is still cropped, but
        all pixel values are set to zero)

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
            aligned_im = im[(lower-y):-(upper+y+1), (right-x):-(left+x+1)]
        else:
            empty_im = np.zeros(im.shape, dtype=im.dtype)
            aligned_im = empty_im[lower:-(upper+1), right:-(left+1)]
        return aligned_im
    except IndexError as e:
        raise IndexError('Shifting and cropping of the image failed!\n'
                         'Shift or overhang values are incorrect:\n%s'
                         % str(e))
    except Exception as e:
        raise Exception('Shifting and cropping of the image failed!\n'
                        'Reason: %s' % str(e))


def shift_and_crop_vips(im, y, x, upper, lower, left, right, shift=True):
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
    upper: int
        upper overhang - pixels cropped at the bottom
    lower: int
        lower overhang - pixels cropped at the top
    left: int
        left overhang - pixels cropped at the right
    right: int
        right overhang - pixels cropped at the left
    shift: bool, optional
        whether image should be shifted (if ``False`` it is still cropped, but
        all pixel values are set to zero)

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
    try:
        if shift:
            aligned_im = im.crop(right-x, lower-y,
                                 im.width-left-right,
                                 im.height-upper-lower)
        else:
            empty_im = Vips.Image.new_from_array(
                            np.zeros(im.height, im.width).tolist()).cast(
                            im.get_format())
            aligned_im = empty_im.crop(right, lower,
                                       im.width-left-right,
                                       im.height-upper-lower)
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

    persistent = {
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
            reference (positive value -> to the right; negative value -> to the
            left)
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
            overhang in pixels at the lower side (bottom) of the image relative
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
            overhang in pixels at the upper side (top) of the image relative
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
            overhang in pixels at the right side of the image relative
            to its reference: pixels to crop at the left side of the image
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
            overhang in pixels at the left side of the image relative
            to its reference: pixels to crop at the right side of the image
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
            if a in ShiftDescription.persistent:
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
        missing_keys = [a for a in ShiftDescription.persistent
                        if a not in description.keys()]
        if len(missing_keys) > 0:
            raise KeyError('Missing keys: "%s"' % '", "'.join(missing_keys))
        for k, v in description.iteritems():
            if k not in ShiftDescription.persistent:
                raise AttributeError(
                        'Class "%s" has no attribute "%s"'
                        % (ShiftDescription.__class__.__name__, k))
            setattr(self, k, v)
