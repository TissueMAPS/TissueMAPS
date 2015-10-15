import numpy as np
from gi.repository import Vips
from abc import ABCMeta
from abc import abstractmethod
from abc import abstractproperty
from . import image_utils
from .align import shift
from .corilla import illumcorr
from .illuminati import segment
from .readers import VipsImageReader
from .readers import NumpyImageReader


class Pixels(object):

    '''
    Abstract base class for a pixel array.

    See also
    --------
    `tmlib.pixels.VipsPixels`_
    `tmlib.pixels.NumpyPixels`_
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
    def save_as_png(self, filename):
        pass


class VipsPixels(Pixels):

    '''
    Class for a pixel array of type `Vips.Image`.
    '''

    def __init__(self, array):
        '''
        Initialize an instance of class VipsPixels.

        Parameters
        ----------
        array: Vips.Image
            image pixel array
        '''
        super(VipsPixels, self).__init__(array)
        self.array = array

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
        VipsPixels
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
        VipsPixels
            new pixel object without the specified objects
        '''
        return VipsPixels(segment.remove_objects_vips(self.array, ids))

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
        VipsPixels
            aligned pixel object

        Warning
        -------
        The aligned image may have different dimensions.
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
        VipsPixels
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
        VipsPixel
            pixel object

        See also
        --------
        `tmlib.readers.VipsImageReader`_
        '''
        with VipsImageReader() as reader:
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
        VipsPixel
            pixel object
        '''
        return VipsPixels(Vips.Image.new_from_array(array.tolist()))

    def save_as_png(self, filename):
        '''
        Write image to disk as PNG file.

        Parameters
        ----------
        filename: str
            absolute path to output file
        '''
        image_utils.save_image_png_vips(self.array, filename)


class NumpyPixels(Pixels):

    '''
    Class for a pixel array of type `numpy.ndarray`.
    '''

    def __init__(self, array):
        '''
        Initialize an instance of class NumpyPixels.

        Parameters
        ----------
        array: numpy.ndarray
            image pixel array
        '''
        super(NumpyPixels, self).__init__(array)
        self.array = array

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
        NumpyPixels
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
        NumpyPixels
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
        NumpyPixels
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
                    shift=not(sd.omit), crop=crop))

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
        NumpyPixels
            corrected pixel object
        '''
        return NumpyPixels(illumcorr.illum_correct_numpy(
                    self.array, mean_image, std_image))

    @staticmethod
    def create_from_file(filename):
        '''
        Read an image from file and create an instance of class NumpyPixel.

        Parameters
        ----------
        filename: str
            absolute path to the image file

        Returns
        -------
        NumpyPixels
            pixel object

        See also
        --------
        `tmlib.readers.NumpyImageReader`_
        '''
        with NumpyImageReader() as reader:
            return NumpyPixels(reader.read(filename))

    def save_as_png(self, filename):
        '''
        Write image to disk as PNG file.

        Parameters
        ----------
        filename: str
            absolute path to output file
        '''
        image_utils.save_image_png_numpy(self.array, filename)
