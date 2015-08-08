import numpy as np
from gi.repository import Vips


def shift_and_crop_image(im, y, x, upper, lower, left, right, shift=True):
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
    numpy.array or Vips.Image
        shifted and cropped image

    Raises
    ------
    IndexError
        when shift or overhang values are too extreme
    Exception
        when it fails for unknown reasons
    '''
    try:
        if isinstance(im, np.ndarray):
            if shift:
                aligned_im = im[(lower-y):-(upper+y+1), (right-x):-(left+x+1)]
            else:
                empty_im = np.zeros(im.shape, dtype=im.dtype)
                aligned_im = empty_im[lower:-(upper+1), right:-(left+1)]
        else:
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
    Class for shift description for an image.

    A shift description consists of shift and overhang values as well as
    additional metainformation that are based on the registration of an
    image acquired at the same position with a corresponding image
    of the reference cycle.

    See also
    --------
    `corilla`_
    '''

    def __init__(self, description):
        '''
        Initialize an instance of class ShiftDescription.

        Parameters
        ----------
        description: Dict[str, int or str or bool]
            content of the shift description file

        See also
        --------
        `tmt.config`_
        '''
        self.description = description

    @property
    def x_shift(self):
        '''
        Returns
        -------
        int
            shift of the image in pixels in x direction relative to its
            reference (positive value -> to the right; negative value -> to the
            left)

        Raises
        ------
        KeyError
            when `description` does not contain "x_shift"
        '''
        if 'x_shift' not in self.description:
            raise KeyError('Descriptor must contain '
                           '"x_shift" information.')
        self._x_shift = self.description['x_shift']
        return self._x_shift

    @property
    def y_shift(self):
        '''
        Returns
        -------
        int
            shift of the image in pixels in y direction relative to its
            reference (positive value -> downwards; negative value -> upwards)

        Raises
        ------
        KeyError
            when `description` does not contain "y_shift"
        '''
        if 'y_shift' not in self.description:
            raise KeyError('Descriptor must contain '
                           '"y_shift" information.')
        self._y_shift = self.description['y_shift']
        return self._y_shift

    @property
    def lower_overhang(self):
        '''
        Returns
        -------
        int
            overhang in pixels at the lower side (bottom) of the image relative
            to its reference: pixels to crop at the top of the image

        Raises
        ------
        KeyError
            when `description` does not contain "lower_overhang"
        '''
        if 'lower_overhang' not in self.description:
            raise KeyError('Descriptor must contain '
                           '"lower_overhang" information.')
        self._lower_overhang = self.description['lower_overhang']
        return self._lower_overhang

    @property
    def upper_overhang(self):
        '''
        Returns
        -------
        int
            overhang in pixels at the upper side (top) of the image relative
            to its reference: pixels to crop at the bottom of the image

        Raises
        ------
        KeyError
            when `description` does not contain "upper_overhang"
        '''
        if 'upper_overhang' not in self.description:
            raise KeyError('Descriptor must contain '
                           '"upper_overhang" information.')
        self._upper_overhang = self.description['upper_overhang']
        return self._upper_overhang

    @property
    def right_overhang(self):
        '''
        Returns
        -------
        int
            overhang in pixels at the right side of the image relative
            to its reference: pixels to crop at the left side of the image

        Raises
        ------
        KeyError
            when `description` does not contain "right_overhang"
        '''
        if 'right_overhang' not in self.description:
            raise KeyError('Descriptor must contain '
                           '"right_overhang" information.')
        self._right_overhang = self.description['right_overhang']
        return self._right_overhang

    @property
    def left_overhang(self):
        '''
        Returns
        -------
        int
            overhang in pixels at the left side of the image relative
            to its reference: pixels to crop at the right side of the image

        Raises
        ------
        KeyError
            when `description` does not contain "left_overhang"
        '''
        if 'left_overhang' not in self.description:
            raise KeyError('Descriptor must contain '
                           '"left_overhang" information.')
        self._left_overhang = self.description['left_overhang']
        return self._left_overhang

    @property
    def dont_shift(self):
        '''
        Returns
        -------
        bool
            whether the image should be shifted (``False`` means that the
            shift values for this site exceed the maximally tolerated shift)

        Raises
        ------
        KeyError
            when `description` does not contain "dont_shift"
        '''
        if 'dont_shift' not in self.description:
            raise KeyError('Descriptor must contain '
                           '"dont_shift" information.')
        self._dont_shift = self.description['dont_shift']
        return self._dont_shift

    @property
    def cycle(self):
        '''
        Returns
        -------
        int
            cycle identifier number

        Raises
        ------
        KeyError
            when `description` does not contain "cycle"
        '''
        if 'cycle' not in self.description:
            raise KeyError('Descriptor must contain '
                           '"cycle" information.')
        self._cycle = self.description['cycle']
        return self._cycle

    @property
    def filename(self):
        '''
        Returns
        -------
        str
            name of the image file that was used for registration

        Raises
        ------
        KeyError
            when `description` does not contain "filename"
        '''
        if 'filename' not in self.description:
            raise KeyError('Descriptor must contain '
                           '"filename" information.')
        self._filename = self.description['filename']
        return self._filename

    def align(self, im, im_name):
        '''
        Align, i.e. shift and crop, an image based on calculated shift
        and overhang values.

        Parameters
        ----------
        im: numpy.ndarray or Vips.Image
            input image that should be aligned
        im_name: str
            name of the image file

        Returns
        -------
        numpy.ndarray or Vips.Image
            aligned image
        '''
        shifted_im = shift_and_crop_image(im, y=self.y_shift, x=self.x_shift,
                                          upper=self.upper_overhang,
                                          lower=self.lower_overhang,
                                          left=self.left_overhang,
                                          right=self.right_overhang,
                                          shift=not(self.dont_shift))
        return shifted_im
