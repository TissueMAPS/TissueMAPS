import re
import numpy as np
from gi.repository import Vips
from illumstats import illum_correct


SUPPORTED_IMAGE_FILES = ['png', 'jpg', 'tiff', 'tif', 'jpeg']

# A regexp to detect supported files. Used to filter images in a folder_name.
_image_regex = re.compile('.*(' + '|'.join(
    ['\\.' + ext for ext in SUPPORTED_IMAGE_FILES]) + ')$', re.IGNORECASE)


def is_image_file(filename):
    '''
    Check if filename ends with a supported file extension.

    Parameters
    ----------
    filename: str
    '''
    return _image_regex.match(filename)


class Pixels(object):

    '''
    Class for a pixels grid, i.e. a 2D image array object.

    2D means that the image doesn't contain any z-stacks.
    However, the image array may still have more than 2 dimensions.
    The 3rd dimension represents color and is referred to "bands".
    '''

    def __init__(self, image):
        '''
        Initialize an instance of class Pixels.

        Parameters
        ----------
        image: numpy.ndarray or Vips.Image
            pixel array
        '''
        self.image = image

    @property
    def dimensions(self):
        '''
        Returns
        -------
        Tuple[int]
            y, x dimensions of the pixels array
        '''
        if isinstance(self.image, Vips.Image):
            self._dimensions = (self.image.height, self.image.width)
        else:
            # All other libraries return numpy arrays
            self._dimensions = self.image.shape[0:2]
        return self._dimensions

    @property
    def bands(self):
        '''
        Bands represent colors. An RGB image has 3 bands while a greyscale
        image has only one band.

        Returns
        -------
        int
            number of bands of the pixel array
        '''
        if isinstance(self.image, Vips.Image):
            self._bands = self.image.bands
        else:
            if len(self.image.shape) > 2:
                self._bands = self.image.shape[2]
            else:
                self._bands = 1
        return self._bands

    @property
    def type(self):
        '''
        Returns
        -------
        str
            type (class) of the pixel array, e.g. "numpy.ndarray"
        '''
        self._type = type(self.image)
        return self._type

    @property
    def dtype(self):
        '''
        Returns
        -------
        str
            data type of the pixel array elements, e.g. "uint16"
        '''
        if isinstance(self.image, Vips.Image):
            self._type = self.image.get_format()
        else:
            # All other libraries return numpy arrays
            self._type = self.image.dtype
        return self._type

    def align(self):
        '''
        Align (shift and crop) the image based on pre-calculated shift and
        overlap values.

        .. Warning::

            Alignment may change the dimensions of the image.
        '''
        # TODO
        pass


class ChannelImage(Pixels):

    '''
    Class for a channel image, i.e. a 2D greyscale image with a single band.
    '''

    def __init__(self, image):
        '''
        Initialize an instance of class ChannelImage.

        Parameters
        ----------
        image: numpy.ndarray or Vips.Image
            pixel array of unsigned integer type

        Raises
        ------
        ValueError
            when `image` has more than one band
        TypeError
            when data type of `image` is not an unsigned integer type

        See also
        --------
        `image.Pixels`_
        '''
        Pixels.__init__(self, image)
        self.image = image
        if self.bands > 1:
            raise ValueError('A channel image can only have a single band.')
        if self.type == 'Vips.Image':
            if not Vips.BandFormat.isuint(self.image.get_format()):
                raise TypeError('Format of the Vips image must be an '
                                'unsigned integer type.')
        else:
            if not (self.image.dtype == np.uint16
                    or self.image.dtype == np.uint8):
                raise TypeError('Data type of the numpy array must be an '
                                'unsigned integer type.')

    def correct(self, mean_mat, std_mat):
        '''
        Correct the image for illumination artifacts based on pre-calculated
        illumination statistics.

        Parameters
        ----------
        mean_mat: numpy.ndarray[numpy.float64] or Vips.Image[Vips.BandFormat.DOUBLE]
            matrix of mean values (same dimensions and type as the image)
        std_mat: numpy.ndarray[numpy.float64] or Vips.Image[Vips.BandFormat.DOUBLE]
            matrix of standard deviation values (same dimensions and type
            as the image)

        Raises
        ------
        TypeError
            when `mean_mat` and `std_mat` don't have same type as the image
        ValueError
            when `mean_mat` and `std_mat` don't have same dimensions
            as the image

        See also
        --------
        `illumstats`_
        '''
        statistics_mats = [mean_mat, std_mat]
        if not all([isinstance(m, self.type) for m in statistics_mats]):
            raise TypeError('Statistics matrices must have same '
                            'type as the image')
        if self.type == 'Vips.Image':
            if not all([self.dimensions != (m.height, m.width)
                        for m in statistics_mats]):
                raise ValueError('Statistics matrices must have same '
                                 'dimensions as the image')
        else:
            if not all([self.dimensions != m.shape for m in statistics_mats]):
                raise ValueError('Statistics matrices must have same '
                                 'dimensions as the image')

        corrected_image = illum_correct(self.image, mean_mat, std_mat)
        return corrected_image


class BrightfieldImage(Pixels):

    '''
    Class for a brightfield image, i.e. a 2D RGB image with three bands.
    '''

    def __init__(self, image):
        '''
        Initialize an instance of class BrightfieldImage.

        Parameters
        ----------
        image: numpy.ndarray or Vips.Image
            pixel array

        Raises
        ------
        ValueError
            when `image` doesn't have three bands

        See also
        --------
        `image.Pixels`_
        '''
        Pixels.__init__(self, image)
        if self.bands != 3:
            raise ValueError('A brightfield image must have 3 bands.')
        self.image = image


class MaskImage(Pixels):

    '''
    Class for a mask image, i.e. a 2D binary segmentation image
    with a single band.
    '''

    def __init__(self, image):
        '''
        Initialize an instance of class MaskImage.

        .. Note::

            `image` is converted to a binary image

        Parameters
        ----------
        image: numpy.ndarray or Vips.Image
            pixel array

        Raises
        ------
        ValueError
            when `image` has more than one band

        See also
        --------
        `image.Pixels`_
        '''
        # make the image binary
        Pixels.__init__(self, image > 0)
        self.image = image > 0
        if self.bands > 1:
            raise ValueError('A mask image can only have a single band.')


class LabelImage(Pixels):

    '''
    Class for a labeled image, i.e. a 2D segmented image,
    where each object (connected component) is labeled with a unique identifier.
    The labeling can be encoded in a single band or in multiple bands
    (which may become necessary when the number of objects exceeds the depth
     of the image, e.g. a greyscale 16-bit image one only encode 2^16 objects).
    '''

    def __init__(self, image):
        '''
        Initialize an instance of class LabelImage.

        Parameters
        ----------
        image: numpy.ndarray or Vips.Image
            pixel array

        Raises
        ------
        ValueError
            when `image` doesn't have one or three bands

        See also
        --------
        `image.Pixels`_
        '''
        # binary pixel array
        Pixels.__init__(self, image)
        self.image = image
        if self.bands != 1 or self.bands != 3:
            raise ValueError('A mask image can either have a single band '
                             'or three bands.')

    def objects(self):
        '''
        Regionprops elements.
        '''
        # TODO
        pass
