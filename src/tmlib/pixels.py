import numpy as np
import scipy.ndimage as ndi
from gi.repository import Vips
import skimage
from abc import ABCMeta
from abc import abstractmethod
from abc import abstractproperty
from . import image_utils
from .align import shift
from .corilla import illumcorr
from .illuminati import segment
from .readers import VipsReader
from .readers import NumpyReader
from .writers import VipsWriter
from .writers import NumpyWriter


class Pixels(object):

    '''
    Abstract base class for a 2D pixel array.

    See also
    --------
    :py:class:`tmlib.pixels.VipsPixels`
    :py:class:`tmlib.pixels.NumpyPixels`
    '''

    __metaclass__ = ABCMeta

    def __init__(self, array):
        self.array = array

    @abstractproperty
    def dimensions(self):
        pass

    @abstractproperty
    def bands(self):
        pass

    @property
    def type(self):
        self._type = type(self.array)
        return self._type

    @abstractproperty
    def dtype(self):
        pass

    @abstractproperty
    def is_float(self):
        pass

    @abstractproperty
    def is_uint(self):
        pass

    @abstractproperty
    def is_binary(self):
        pass

    @abstractmethod
    def get_outlines(self, keep_ids):
        pass

    @abstractproperty
    def n_objects(self):
        pass

    @abstractmethod
    def remove_objects(self, ids):
        pass

    @abstractmethod
    def align(self, shift_description):
        pass

    @abstractmethod
    def correct_illumination(self, mean_image, std_image):
        pass

    @abstractmethod
    def write_to_file(self, filename):
        pass

    @abstractmethod
    def extract(self, y_offset, x_offset, height, width):
        pass

    @abstractmethod
    def clip(self, threshold):
        pass

    @abstractmethod
    def scale(self, threshold):
        pass

    @abstractmethod
    def join(self, pixels, direction):
        pass

    @abstractmethod
    def merge(self, pixels, direction, offset):
        pass

    @abstractmethod
    def add_background(self, n, side):
        pass

    @abstractmethod
    def smooth(self, sigma):
        pass

    def shrink(self, factor):
        pass

    @abstractmethod
    def create_from_file(filename):
        pass

    @abstractmethod
    def create_as_background(y_dimension, x_dimension, dtype):
        pass


class VipsPixels(Pixels):

    '''
    Class for a pixel array of type :py:class:`Vips.Image`.
    '''

    def __init__(self, array):
        '''
        Parameters
        ----------
        array: gi.overrides.Vips.Image
            image pixel array
        '''
        if not isinstance(array, Vips.Image):
            raise TypeError('Argument array must have type Vips.Image')
        super(VipsPixels, self).__init__(array)

    @property
    def dimensions(self):
        '''
        Returns
        -------
        Tuple[int]
            y, x dimensions of the pixel array
        '''
        self._dimensions = (self.array.height, self.array.width)
        return self._dimensions

    @property
    def bands(self):
        '''
        Bands represent colors. An RGB image has 3 bands while a greyscale
        image has only one band.

        Returns
        -------
        int
            number of bands in the pixel array
        '''
        self._bands = self.array.bands
        return self._bands

    @property
    def dtype(self):
        '''
        Returns
        -------
        str
            data type (format) of the pixel array elements
        '''
        self._dtype = self.array.get_format()
        return self._dtype

    @property
    def is_float(self):
        '''
        Returns
        -------
        bool
            whether pixel array has float data type
            (Vips.BandFormat.FLOAT or Vips.BandFormat.DOUBLE)
        '''
        self._is_float = Vips.BandFormat.isfloat(self.dtype)
        return self._is_float

    @property
    def is_uint(self):
        '''
        Returns
        -------
        bool
            whether pixel array has unsigned integer data type
            (Vips.BandFormat.UCHAR or Vips.BandFormat.USHORT)
        '''
        self._is_uint = Vips.BandFormat.isuint(self.dtype)
        return self._is_uint

    @property
    def is_binary(self):
        '''
        Returns
        -------
        bool
            whether pixel array has boolean data type
            (Vips.BandFormat.UCHAR)
        '''
        self._is_binary = self.dtype == Vips.BandFormat.UCHAR
        return self._is_binary

    def get_outlines(self, keep_ids):
        '''
        Obtain the outlines of objects in the image.

        Parameters
        ----------
        keep_ids: bool
            whether the ids (pixel values) of objects should be preserved;
            returns unsigned integer type if ``True`` and binary type otherwise

        Returns
        -------
        tmlib.pixels.VipsPixels
            new pixel object
        '''
        outlines = segment.compute_outlines_vips(self.array)
        if keep_ids:
            outlines = outlines.ifthenelse(self.array, 0)
        return VipsPixels(outlines)

    @property
    def n_objects(self):
        '''
        Returns
        -------
        int
            number of objects (labeled connected components) in the image
        '''
        img_numpy = image_utils.vips_image_to_np_array(self.array)
        self._n_objects = len(np.unique(img_numpy[img_numpy > 0]))
        # TODO: obtain the number of unique pixel values in Vips?
        return self._n_objects

    def remove_objects(self, ids):
        '''
        Remove certain objects from the image.

        Parameters
        ----------
        ids: List[int]
            ids of objects that should be removed

        Returns
        -------
        tmlib.pixels.VipsPixels
            new pixel object without the specified objects
        '''
        return VipsPixels(segment.remove_objects_vips(self.array, ids))

    def align(self, shift_description, crop=True):
        '''
        Align the image based on prior registration.

        Parameters
        ----------
        shift_description: dict
            shift and overhang values
        crop: bool, optional
            whether images should cropped or rather padded
            with zero valued pixels (default: ``True``)

        Returns
        -------
        tmlib.pixels.VipsPixels
            aligned pixel object

        Warning
        -------
        The aligned image may have different dimensions.

        See also
        --------
        :py:class:`tmlib.align.description.AligmentDescription`
        '''
        sd = shift_description
        # TODO
        return VipsPixels(shift.shift_and_crop_vips(
                    self.array, y=sd.y_shift, x=sd.x_shift,
                    bottom=sd.upper_overhang, top=sd.lower_overhang,
                    right=sd.left_overhang, left=sd.right_overhang,
                    shift=not(sd.is_omitted), crop=crop))

    def correct_illumination(self, mean, std):
        '''
        Correct image for illumination artifacts based on pre-calculated
        statistics.

        Parameters
        ----------
        mean: Vips.Image
            mean values
        std: Vips.Image
            standard deviation values

        Returns
        -------
        tmlib.pixels.VipsPixels
            corrected pixel object
        '''
        return VipsPixels(illumcorr.illum_correct_vips(
                    self.array, mean, std))

    @staticmethod
    def create_from_file(filename):
        '''
        Read an image from file and create an instance of class VipsPixel.

        Parameters
        ----------
        filename: str
            absolute path to the image file

        Returns
        -------
        tmlib.pixels.VipsPixel
            pixels object

        See also
        --------
        :py:class:`tmlib.readers.VipsReader`
        '''
        with VipsReader() as reader:
            return VipsPixels(reader.read(filename))

    @staticmethod
    def create_from_numpy_array(array):
        '''
        Create an instance of class VipsPixel from a `numpy` array.

        Parameters
        ----------
        array: numpy.ndarray

        Returns
        -------
        tmlib.pixels.VipsPixel
            pixels object

        See also
        --------
        :py:func:`tmlib.image_utils.np_array_to_vips_image`
        '''
        return VipsPixels(image_utils.np_array_to_vips_image(array))

    def write_to_file(self, filename):
        '''
        Write pixels array to file on disk.

        Parameters
        ----------
        filename: str
            absolute path to output file

        See also
        --------
        :py:method:`tmlib.writers.VipsWriter.write`
        '''
        with VipsWriter() as writer:
            writer.write(filename, self.array)

    def extract(self, y_offset, x_offset, height, width):
        '''
        Extract a continuous, rectangular area of pixels from the array.

        Parameters
        ----------
        y_offset: int
            index of the top, left point of the rectangle on the *y* axis
        x_offset: int
            index of the top, left point of the rectangle on the *x* axis
        height: int
            height of the rectangle, i.e. length of the rectangle along the
            *y* axis
        width: int
            width of the rectangle, i.e. length of the rectangle along the
            *x* axis

        Returns
        -------
        tmlib.pixels.VipsPixel
            extracted pixels with dimensions `height` x `width`
        '''
        a = self.array.extract_area(x_offset, y_offset, width, height)
        return VipsPixels(a)

    def clip(self, threshold):
        '''
        Clip intensity values above `threshold`, i.e. set all pixel values
        above `threshold` to `threshold`.

        Parameters
        ----------
        threshold: int
            value above which pixel values should be clipped

        Returns
        -------
        tmlib.pixels.VipsPixels
            clipped pixels
        '''
        if self.dtype == Vips.BandFormat.USHORT:
            lut = Vips.Image.identity(ushort=True)
        elif self.dtype == Vips.BandFormat.UCHAR:
            lut = Vips.Image.identity()
        else:
            TypeError(
                    'Only pixels with dtype "ushort" and "uchar" '
                    'can be clipped.')
        condition_image = (lut >= threshold)
        lut = condition_image.ifthenelse(threshold, lut)
        a = self.array.maplut(lut)
        return VipsPixels(a)

    def scale(self, threshold):
        '''
        Scale the pixel values to 8-bit such that `threshold` is 255.

        Parameters
        ----------
        threshold: int
            value above which pixel values will be set to 255, i.e.
            the range [0, `threshold`] will be mapped to range [0, 255]
        '''
        if self.dtype == Vips.BandFormat.USHORT:
            lut = Vips.Image.identity(ushort=True)
        elif self.dtype == Vips.BandFormat.UCHAR:
            # Is already 8-bit
            return self
        else:
            TypeError(
                    'Only pixels with dtype "ushort" or "uchar" '
                    'can be scaled to 8-bit.')
        for i in range(256):
            lower = threshold / 256 * i
            upper = threshold / 256 * (i+1)
            condition_image = (lower < lut < upper)
            lut = condition_image.ifthenelse(i, lut)
        a = self.array.maplut(lut)
        return VipsPixels(a)

    def join(self, pixels, direction):
        '''
        Join a pixels object to the existing.

        Parameters
        ----------
        pixels: tmlib.pixels.NumpyPixels
            pixels object that should be joined with the existing object
        direction: str
            direction along which the two pixels arrays should be joined,
            either ``"horizontal"`` or ``"vertical"``

        Returns
        -------
        tmlib.pixels.VipsPixel
            joined pixels
        '''
        if direction == 'vertical':
            a = self.array.join(pixels.array, 'vertical')
        elif direction == 'horizontal':
            a = self.array.join(pixels.array, 'horizontal')
        else:
            raise ValueError(
                        'Argument "direction" must be either '
                        '"horizontal" or "vertical"')
        return VipsPixels(a)

    def merge(self, pixels, direction, offset):
        '''
        Merge two pixels arrays into one.

        Parameters
        ----------
        pixels: tmlib.pixels.NumpyPixels
            pixels object that should be merged with the existing object
        direction: str
            direction along which the two pixels arrays should be merged,
            either ``"horizontal"`` or ``"vertical"``
        offset: int
            offset for `pixels` in the existing object

        Parameters
        ----------
        tmlib.pixels.VipsPixels
            merged pixels
        '''
        if direction == 'vertical':
            height = self.array.dimensions[0] - offset
            width = self.array.dimensions[1]
            a = self.array.embed(pixels.array, 0, offset, width, height)
        elif direction == 'horizontal':
            height = self.array.dimensions[0]
            width = self.array.dimensions[1] - offset
            a = self.array.embed(pixels.array, offset, 0, width, height)
        else:
            raise ValueError(
                        'Argument "direction" must be either '
                        '"horizontal" or "vertical"')
        return VipsPixels(a)

    def add_background(self, n, side):
        '''
        Add zero value pixels to one `side` of the pixels array.

        Parameters
        ----------
        n: int
            number of pixels that should be added along the given axis
        side: str
            side of the array that should be padded;
            either ``"top"``, ``"bottom"``, ``"left"``, or ``"right"``

        Returns
        -------
        tmlib.pixels.VipsPixels
            pixels with added background
        '''
        if side == 'top':
            a = Vips.Image.black(self.dimensions[1], n, bands=1)
            a = a.join(self.array, 'vertical')
        elif side == 'bottom':
            a = Vips.Image.black(self.dimensions[1], n, bands=1)
            a = self.array.join(a, 'vertical')
        elif side == 'left':
            a = Vips.Image.black(n, self.dimensions[0], bands=1)
            a = a.join(self.array, 'horizontal')
        elif side == 'right':
            a = Vips.Image.black(n, self.dimensions[0], bands=1)
            a = self.array.join(a, 'horizontal')
        return VipsPixels(a)

    def smooth(self, sigma):
        '''
        Apply a Gaussian smoothing filter to the pixels array.

        Parameters
        ----------
        sigma: int
            size of the standard deviation of the Gaussian kernel

        Returns
        -------
        tmlib.pixels.VipsPixels
            smoothed pixels
        '''
        a = self.array.gaussblur(sigma)
        return VipsPixels(a)

    def shrink(self, factor):
        '''
        Reduce the size of the pixels.

        Parameters
        ----------
        factor: int
            factor by which the size of the pixels array should be reduced

        Returns
        -------
        tmlib.pixels.VipsPixels
            shrunken pixels
        '''
        a = self.array.shrink(factor, factor)
        return VipsPixels(a)

    @staticmethod
    def create_from_file(filename):
        '''
        Create an object of class :py:class:`tmlib.pixels.VipsPixels`
        from an image file.

        Parameters
        ----------
        filename: str
            absolute path to the file

        Returns
        -------
        tmlib.pixels.VipsPixels
            pixels with array contained in file
        '''
        with VipsReader() as reader:
            return VipsPixels(reader.read(filename))

    @staticmethod
    def create_as_background(y_dimension, x_dimension, dtype):
        '''
        Create an object of class :py:class:`tmlib.pixels.VipsPixels`
        with a background array, i.e. zero values.

        Parameters
        ----------
        y_dimension: int
            length of the array along the y-axis
        x_dimension: int
            length of the array along the x-axis
        dtype: type
            data type of the array

        Returns
        -------
        tmlib.pixels.VipsPixels
            pixels with background array
        '''
        a = Vips.Image.black(x_dimension, y_dimension, bands=1).cast(dtype)
        return VipsPixels(a)


class NumpyPixels(Pixels):

    '''
    Class for a pixel array of type :py:class:`numpy.ndarray`.
    '''

    def __init__(self, array):
        '''
        Parameters
        ----------
        array: numpy.ndarray
            image pixel array

        Returns
        -------
        tmlib.pixels.NumpyPixels
        '''
        if not isinstance(array, np.ndarray):
            raise TypeError('Argument array must have type numpy.ndarray')
        super(NumpyPixels, self).__init__(array)

    @property
    def dimensions(self):
        '''
        Returns
        -------
        Tuple[int]
            y, x dimensions of the pixel array
        '''
        self._dimensions = self.array.shape[0:2]
        return self._dimensions

    @property
    def bands(self):
        '''
        Bands represent colors. An RGB image has 3 bands while a greyscale
        image has only one band.

        Returns
        -------
        int
            number of bands in the pixel array
        '''
        if len(self.array.shape) > 2:
            self._bands = self.array.shape[2]
        else:
            self._bands = 1
        return self._bands

    @property
    def dtype(self):
        '''
        Returns
        -------
        str
            data type of the pixel array elements
        '''
        self._dtype = self.array.dtype
        return self._dtype

    @property
    def is_float(self):
        '''
        Returns
        -------
        bool
            whether pixel array has float data type (numpy.float)
        '''
        self._is_float = self.dtype == np.float
        return self._is_float

    @property
    def is_uint(self):
        '''
        Returns
        -------
        bool
            whether pixel array has unsigned integer data type
            (numpy.uint8 or numpy.uint16)
        '''
        self._is_uint = self.dtype == np.uint16 or self.dtype == np.uint8
        return self._is_uint

    @property
    def is_binary(self):
        '''
        Returns
        -------
        bool
            whether pixel array has boolean data type (numpy.bool)
        '''
        self._is_binary = self.dtype == np.bool
        return self._is_binary

    def get_outlines(self, keep_ids=False):
        '''
        Obtain the outlines of objects in the image.

        Parameters
        ----------
        keep_ids: bool
            whether the ids (pixel values) of objects should be preserved;
            returns unsigned integer type if ``True`` and binary type otherwise

        Returns
        -------
        tmlib.pixels.NumpyPixels
            new pixel object
        '''
        return NumpyPixels(segment.compute_outlines_numpy(self.array,
                           keep_ids))

    @property
    def n_objects(self):
        '''
        Returns
        -------
        int
            number of objects (labeled connected components) in the image
        '''
        self._n_objects = len(np.unique(self.array[self.array > 0]))
        return self._n_objects

    def remove_objects(self, ids):
        '''
        Remove certain objects from the image.

        Parameters
        ----------
        ids: List[int]
            ids of objects that should be removed

        Returns
        -------
        tmlib.pixels.NumpyPixels
            new pixel object without the specified objects
        '''
        return NumpyPixels(segment.remove_objects_numpy(self.array, ids))

    def align(self, shift_description, crop=True):
        '''
        Align the image based on prior registration.

        Parameters
        ----------
        shift_description: dict
            shift and overlap values
        crop: bool, optional
            whether images should cropped or rather padded
            with zero valued pixels (default: ``True``)

        Returns
        -------
        tmlib.pixels.NumpyPixels
            aligned pixel object

        Warning
        -------
        The aligned image may have different dimensions.
        '''
        sd = shift_description
        return NumpyPixels(shift.shift_and_crop_numpy(
                    self.array, y=sd.y_shift, x=sd.x_shift,
                    bottom=sd.upper_overhang, top=sd.lower_overhang,
                    right=sd.left_overhang, left=sd.right_overhang,
                    shift=not(sd.is_omitted), crop=crop))

    def correct_illumination(self, mean_image, std_image):
        '''
        Correct image for illumination artifacts based on pre-calculated
        statistics.

        Parameters
        ----------
        mean: numpy.ndarray
            mean values
        std: numpy.ndarray
            standard deviation values

        Returns
        -------
        tmlib.pixels.NumpyPixels
            corrected pixel object
        '''
        return NumpyPixels(illumcorr.illum_correct_numpy(
                    self.array, mean_image, std_image))

    @staticmethod
    def create_from_vips_image(array):
        '''
        Create an instance of class NumpyPixel from a `Vips` image.

        Parameters
        ----------
        array: gi.overrides.Vips.Image

        Returns
        -------
        tmlib.pixels.NumpyPixel
            pixels object

        See also
        --------
        :py:func:`tmlib.image_utils.vips_image_to_np_array`
        '''
        return NumpyPixels(image_utils.vips_image_to_np_array(array))

    def write_to_file(self, filename):
        '''
        Write pixels array to file on disk.

        The format depends on the file extension:
            - *.png for PNG (8-bit and 16-bit)
            - *.tiff or *.tif for TIFF (8-bit and 16-bit)
            - *.jpeg or *.jpg for JPEG (8-bit)
            - *.ppm for PPM (8-bit and 16-bit)

        Parameters
        ----------
        filename: str
            absolute path to output file
        See also
        --------
        :py:method:`tmlib.writers.NumpyWriter.write`
        '''
        with NumpyWriter() as writer:
            writer.write(filename, self.array)

    def extract(self, y_offset, x_offset, height, width):
        '''
        Extract a continuous, rectangular area of pixels from the array.

        Parameters
        ----------
        y_offset: int
            index of the top, left point of the rectangle on the *y* axis
        x_offset: int
            index of the top, left point of the rectangle on the *x* axis
        height: int
            height of the rectangle, i.e. length of the rectangle along the
            *y* axis
        width: int
            width of the rectangle, i.e. length of the rectangle along the
            *x* axis

        Returns
        -------
        tmlib.pixels.NumpyPixel
            extracted pixels with dimensions `height` x `width`
        '''
        a = self.array[y_offset:(y_offset+height), x_offset:(x_offset+width)]
        return NumpyPixels(a)

    def scale(self, threshold):
        '''
        Scale the pixel values to 8-bit such that `threshold` is 255.

        Parameters
        ----------
        threshold: int
            value above which pixel values will be set to 255, i.e.
            the range [0, `threshold`] will be mapped to range [0, 255]

        Returns
        -------
        tmlib.pixels.NumpyPixels
            rescaled pixels
        '''
        if self.dtype == 'uint16':
            a = skimage.exposure.rescale_intensity(
                        self.array,
                        out_range='uint8',
                        in_range=(0, threshold)
            ).astype(np.uint8)
            return NumpyPixels(a)
        elif self.dtype == 'uint8':
            return self
        else:
            TypeError(
                    'Only pixels with dtype "uint16" or "uint8" '
                    'can be scaled to 8-bit.')

    def join(self, pixels, direction):
        '''
        Join two pixels arrays.

        Parameters
        ----------
        pixels: numpy.ndarray
            pixels object that should be joined to the existing
        direction: str
            direction along which the two pixels arrays should be joined,
            either ``"horizontal"`` or ``"vertical"``

        Returns
        -------
        tmlib.pixels.NumpyPixels
            joined pixels
        '''
        if direction == 'vertical':
            a = np.vstack([self.array, pixels.array])
        elif direction == 'horizontal':
            a = np.hstack([self.array, pixels.array])
        else:
            raise ValueError(
                        'Argument "direction" must be either '
                        '"horizontal" or "vertical"')
        return NumpyPixels(a)

    def merge(self, pixels, direction, offset):
        '''
        Merge two pixels arrays into one.

        Parameters
        ----------
        pixels: tmlib.pixels.NumpyPixels
            pixels object that should be merged with the existing object
        direction: str
            direction along which the two pixels arrays should be merged,
            either ``"horizontal"`` or ``"vertical"``
        offset: int
            offset for `pixels` in the existing object

        Parameters
        ----------
        tmlib.pixels.NumpyPixels
            merged pixels
        '''
        a = self.array.copy()
        if direction == 'vertical':
            a[offset:, :] = pixels.array[offset:, :]
        elif direction == 'horizontal':
            a[:, offset:] = pixels.array[:, offset:]
        else:
            raise ValueError(
                        'Argument "direction" must be either '
                        '"horizontal" or "vertical"')
        return NumpyPixels(a)

    def clip(self, threshold):
        '''
        Clip intensity values above `threshold`, i.e. set all pixel values
        above `threshold` to `threshold`.

        Parameters
        ----------
        threshold: int
            value above which pixel values should be clipped

        Returns
        -------
        tmlib.pixels.NumpyPixels
            clipped pixels
        '''
        a = np.clip(self.array, 0, threshold)
        return NumpyPixels(a)

    def add_background(self, n, side):
        '''
        Add zero value pixels to one `side` of the pixels array.

        Parameters
        ----------
        n: int
            number of pixels that should be added along the given axis
        side: str
            side of the array that should be padded;
            either ``"top"``, ``"bottom"``, ``"left"``, or ``"right"``

        Returns
        -------
        tmlib.pixels.NumpyPixels
            pixels with added background
        '''
        if side == 'top':
            a = np.zeros((n, self.dimensions[1]), dtype=self.dtype)
            a = np.vstack([a, self.array])
        elif side == 'bottom':
            a = np.zeros((n, self.dimensions[1]), dtype=self.dtype)
            a = np.vstack([self.array, a])
        elif side == 'left':
            a = np.zeros((self.dimensions[0], n), dtype=self.dtype)
            a = np.hstack([a, self.array])
        elif side == 'right':
            a = np.zeros((self.dimensions[0], n), dtype=self.dtype)
            a = np.hstack([self.array, a])
        else:
            raise ValueError(
                        'Argument "side" must be one of the following: '
                        '"top", "bottom", "left", "right"')
        return NumpyPixels(a)

    def smooth(self, sigma):
        '''
        Apply a Gaussian smoothing filter to the pixels array.

        Parameters
        ----------
        sigma: int
            size of the standard deviation of the Gaussian kernel

        Returns
        -------
        tmlib.pixels.NumpyPixels
            smoothed pixels
        '''
        a = ndi.filters.gaussian_filter(self.array, sigma)
        return NumpyPixels(a)

    def shrink(self, factor):
        '''
        Reduce the size of the pixels.

        Parameters
        ----------
        factor: int
            factor by which the size of the pixels array should be reduced

        Returns
        -------
        tmlib.pixels.NumpyPixels
            shrunken pixels
        '''
        a = skimage.measure.block_reduce(
                    self.array, (factor, factor), func=np.mean)
        return NumpyPixels(a)

    @staticmethod
    def create_from_file(filename):
        '''
        Create an object of class :py:class:`tmlib.pixels.NumpyPixels`
        from an image file.

        Parameters
        ----------
        filename: str
            absolute path to the file

        Returns
        -------
        tmlib.pixels.NumpyPixels
        '''
        with NumpyReader() as reader:
            return NumpyPixels(reader.read(filename))

    @staticmethod
    def create_as_background(y_dimension, x_dimension, dtype):
        '''
        Create an object of class :py:class:`tmlib.pixels.VipsPixels`
        with a background array, i.e. zero values.

        Parameters
        ----------
        y_dimension: int
            length of the array along the y-axis
        x_dimension: int
            length of the array along the x-axis
        dtype: type
            data type of the array

        Returns
        -------
        tmlib.pixels.NumpyPixels
            pixels with background array
        '''
        a = np.zeros((y_dimension, x_dimension), dtype=dtype)
        return NumpyPixels(a)


def create_pixels_from_array(array):
    '''
    Factory function to create an instance of an implementation of the
    :py:class:`tmlib.pixels.Pixels` base class using the provided `array`.

    Parameters
    ----------
    array: numpy.ndarray or Vips.Image
        array for which a `Pixels` object should be created

    Returns
    -------
    tmlib.pixels.Pixels
        pixels object

    Raises
    ------
    TypeError
        when `array` doesn't have type numpy.ndarray or Vips.Image
    '''
    if isinstance(array, np.ndarray):
        return NumpyPixels(array)
    elif isinstance(array, Vips.Image):
        return VipsPixels(array)
    else:
        raise TypeError(
                'Argument "array" must have type numpy.ndarray or Vips.Image')


def create_pixels_from_file(filename, library):
    '''
    Factory function that creates an instance of an
    implementation of the :py:class:`tmlib.pixels.Pixels` base class using
    array loaded from a file.

    Parameters
    ----------
    filename: str
        absolute path to the file
    library: str
        either "numpy" or "vips"

    Returns
    -------
    tmlib.pixels.Pixels
        pixels object
    '''
    if library == 'numpy':
        return NumpyPixels.create_from_file(filename)
    elif library == 'vips':
        return VipsPixels.create_from_file(filename)
    else:
        raise ValueError('Library must be either "numpy" or "vips".')


def create_background_pixels(y_dimension, x_dimension, dtype, library):
    '''
    Factory function that creates an instance of an
    implementation of the :py:class:`tmlib.pixels.Pixels` class for an array
    filled with zeros.

    Parameters
    ----------
    y_dimension: int
        length of the array along the y-axis
    x_dimension: int
        length of the array along the x-axis
    dtype: type
        data type of the array
    library: str
        either "numpy" or "vips"

    Returns
    -------
    tmlib.pixels.Pixels
        pixels object 
    '''
    if library == 'numpy':
        return NumpyPixels.create_as_background(
                                y_dimension, x_dimension, dtype)
    elif library == 'vips':
        return VipsPixels.create_as_background(
                                y_dimension, x_dimension, dtype,)
    else:
        raise ValueError('Library must be either "numpy" or "vips".')
