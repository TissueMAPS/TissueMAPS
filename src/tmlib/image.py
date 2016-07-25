import os
import numpy as np
import scipy.ndimage as ndi
import skimage.filters
import skimage.measure
import skimage.color
from abc import ABCMeta
import logging

from tmlib.utils import assert_type
from tmlib import image_utils

logger = logging.getLogger(__name__)

#: Set[str]: supported image file extensions
SUPPORTED_IMAGE_FILE_EXTENSIONS = {'.png', '.tif', '.tiff', '.jpg', '.jpeg'}


def is_image_file(filename):
    '''Checks if file represents an image based on the file extension.

    Parameters
    ----------
    filename: str
        name of the image file

    Returns
    -------
    bool
        ``True`` if `filename` represents an image and ``False`` otherwise

    See also
    --------
    :py:const:`tmlib.image.SUPPORTED_IMAGE_FILE_EXTENSIONS`
    '''
    return os.path.splitext(filename)[1] in SUPPORTED_IMAGE_FILE_EXTENSIONS


class Image(object):

    '''
    Abstract base class for an image. An image is defined as a 2D pixels or
    3D voxels array.

    Note
    ----
    The first two dimensions are the y, x axes of individual pixel planes.
    The optional third dimension represents either z resolution and is referred
    to as *zlevels* or color, which is referred to as *bands*.
    '''

    __metaclass__ = ABCMeta

    @assert_type(array='numpy.ndarray')
    def __init__(self, array, metadata=None):
        '''
        Parameters
        ----------
        array: numpy.ndarray
            2D pixels or 3D voxels array
        metadata: tmlib.metadata.ImageMetadata, optional
            image metadata (default: ``None``)
        '''
        self.array = array
        self.metadata = metadata

    @property
    def array(self):
        '''numpy.ndarray: pixels/voxels array'''
        return np.squeeze(self._array)

    @array.setter
    def array(self, value):
        if value.ndim == 2:
            self._array = value[..., np.newaxis]
        elif value.ndim == 3:
            self._array = value
        else:
            raise ValueError('An image must be either a 2D or 3D array.')

    @property
    def dimensions(self):
        '''Tuple[int]: y, x, z/c dimensions of the pixels/voxels array'''
        return self._array.shape

    @property
    def dtype(self):
        '''str: data type of voxels array elements'''
        return self.array.dtype

    @property
    def is_int(self):
        '''bool: whether voxels array has integer data type
        '''
        return self.array.dtype == np.int

    @property
    def is_float(self):
        '''bool: whether voxels array has float data type
        '''
        return self.array.dtype == np.float

    @property
    def is_uint(self):
        '''bool: whether voxels array has unsigned integer data type'''
        return self.array.dtype == np.uint16 or self.array.dtype == np.uint8

    @property
    def is_uint8(self):
        '''bool: whether voxels array has 8-bit unsigned integer data type'''
        return self.array.dtype == np.uint8

    @property
    def is_uint16(self):
        '''bool: whether voxels array has 16-bit unsigned integer data type'''
        return self.array.dtype == np.uint16

    @property
    def is_binary(self):
        '''bool: whether voxels array has boolean data type'''
        return self.array.dtype == np.bool

    def iter_planes(self):
        '''Iterates over pixel planes of the image.

        Returns
        -------
        generator

        Examples
        --------
        >>>arr = numpy.zeros((3, 10, 10), dtype=np.uint8)
        >>>img = Image(arr)
        >>>for level, plane in img.iter_planes():
        ...    print zplane
        '''
        for z in range(self.dimensions[2]):
            yield (z, self.__class__(self._array[:, :, z, ...], self.metadata))

    def get_plane(self, index):
        '''Gets an individual pixel plane of the image.

        Parameters
        ----------
        index: int
            zero-based z-resolution or color band index

        Returns
        -------
        tmlib.image.Image
        '''
        return self.__class__(self._array[:, :, index, ...], self.metadata)

    def extract(self, y_offset, height, x_offset, width, z_offset=0, depth=1):
        '''Extracts a continuous, hyperrectangular volumne of voxels
        from the image.

        Parameters
        ----------
        y_offset: int
            index of the top, left point of the hyperrectangle on the *y* axis
        height: int
            height of the hyperrectangle, i.e. length of the hyperrectangle
            along the *y* axis
        x_offset: int
            index of the top, left point of the hyperrectangle on the *x* axis
        width: int
            width of the hyperrectangle, i.e. length of the hyperrectangle along
            the *x* axis
        z_offset: int, optional
            index of the top, left point of the hyperrectangle on the *z* axis
            (default: ``0``)
        width: int
            depth of the hyperrectangle, i.e. length of the hyperrectangle
            along the *z* axis (default: ``1``)

        Returns
        -------
        tmlib.image.Image
            extracted image with dimensions `height` x `width` x `depth`
        '''
        arr = self._array[
                y_offset:(y_offset+height),
                x_offset:(x_offset+width),
                z_offset:(z_offset+depth),
                ...
        ]
        return self.__class__(arr, self.metadata)

    @assert_type(image='tmlib.image.Image')
    def insert(self, image, y_offset, x_offset, z_offset=0, inplace=True):
        '''Inserts a continuous, hyperrectangular volume of voxels into
        an image.

        Parameters
        ----------
        image: tmlib.image.Image
            image whose voxels should be inserted
        y_offset: int
            index of the top, left point of the hyperrectangle on the *y* axis
        x_offset: int
            index of the top, left point of the hyperrectangle on the *x* axis
        z_offset: int, optional
            index of the top, left point of the hyperrectangle on the *z* axis
            (default: ``0``)
        inplace: bool, optional
            insert voxels into the existing image rather than into a copy
            (default: ``True``)

        Returns
        -------
        tmlib.image.Image
            modified image
        '''
        if (image.dimensions[0] + y_offset > self.dimensions[0] or
                image.dimensions[1] + x_offset > self.dimensions[1] or
                image.dimensions[2] + z_offset > self.dimensions[2]):
            raise ValueError('Image doesn\'t fit.')
        if inplace:
            arr = self._array
        else:
            arr = self._array.copy()
        height, width, depth = image.dimensions
        arr[
            y_offset:(y_offset+height),
            x_offset:(x_offset+width),
            z_offset:(z_offset+depth),
            ...
        ] = image._array
        if inplace:
            return self
        else:
            return self.__class__(arr, self.metadata)

    @assert_type(image='tmlib.image.Image')
    def merge(self, image, axis, offset, inplace=True):
        '''Merges pixels/voxels arrays of two images into one.

        Parameters
        ----------
        image: tmlib.image.Image
            image object whose values should used for merging
        axis: str
            axis along which the two images should be merged,
            either ``"x"``, ``"y"``, or ``"z"``
        offset: int
            offset for `image` in the existing object
        inplace: bool, optional
            merge values into the existing image rather than into a copy
            (default: ``True``)

        Parameters
        ----------
        tmlib.image.Image
            rescaled image
        '''
        if inplace:
            arr = self._array
        else:
            arr = self._array.copy()
        if axis == 'y':
            arr[offset:, :, :, ...] = image._array[offset:, :, :, ...]
        elif axis == 'x':
            arr[:, offset:, :, ...] = image._array[:, offset:, :, ...]
        elif axis == 'z':
            arr[:, :, offset:, ...] = image._array[:, :, offset:, ...]
        else:
            raise ValueError('Unknown axis.')
        if inplace:
            return self
        else:
            return self.__class__(arr, self.metadata)

    @assert_type(image='tmlib.image.Image')
    def join(self, image, axis):
        '''Joins two pixels/voxels arrays.

        Parameters
        ----------
        image: tmlib.image.Image
            image object whose values should be joined
        axis: str
            axis along which the two images should be merged,
            either ``"x"``, ``"y"``, or ``"z"``

        Returns
        -------
        tmlib.image.Image
            joined image
        '''
        # Numpy's nomenclature is different, it would stack the "z" dimension
        # along the first axis. This would make indexing harder in case the
        # image has only two dimensions. There could result in worse
        # performance, though.
        if axis == 'y':
            arr = np.vstack([self._array, image._array])
        elif axis == 'x':
            arr = np.hstack([self._array, image._array])
        elif axis == 'z':
            arr = np.dstack([self._array, image._array])
        else:
            raise ValueError('Unknown axis.')
        return self.__class__(arr, self.metadata)

    def pad_with_background(self, n, side):
        '''Pads one side of the pixels/voxels array with zero values.

        Parameters
        ----------
        n: int
            number of pixels/voxels that should be added along the given axis
        side: str
            side of the array that should be padded relative to the y, x axis
            of an individual plane; either ``"top"``, ``"bottom"``, ``"left"``,
            ``"right"``, ``"front"`` or ``"back"``

        Returns
        -------
        tmlib.image.Image
            padded image
        '''
        if self.dimensions[2] > 1:
            raise ValueError('Not supported for color images.')
        height, width, depth = self.dimensions
        if side == 'top':
            arr = np.zeros((n, width, depth), dtype=self.dtype)
            arr = np.vstack([arr, self._array])
        elif side == 'bottom':
            arr = np.zeros((n, width, depth), dtype=self.dtype)
            arr = np.vstack([self._array, arr])
        elif side == 'left':
            arr = np.zeros((height, n, depth), dtype=self.dtype)
            arr = np.hstack([arr, self._array])
        elif side == 'right':
            arr = np.zeros((height, n, depth), dtype=self.dtype)
            arr = np.hstack([self._array, arr])
        elif side == 'front':
            arr = np.zeros((height, width, n), dtype=self.dtype)
            arr = np.dstack([self._array, arr])
        elif side == 'back':
            arr = np.zeros((height, width, n), dtype=self.dtype)
            arr = np.dstack([self._array, arr])
        else:
            raise ValueError('Unknown side.')
        return self.__class__(arr, self.metadata)

    def smooth(self, sigma):
        '''Applies a Gaussian smoothing filter to the pixels/voxels array.

        Parameters
        ----------
        sigma: int
            size of the standard deviation of the Gaussian kernel

        Returns
        -------
        tmlib.image.Image
            smoothed image
        '''
        arr = skimage.filters.gaussian(self._array, sigma)
        return self.__class__(arr, self.metadata)

    def shrink(self, factor):
        '''Shrinks the first two dimensions of the pixels/voxels array
        by `factor`. Pixels/voxels values of the aggregated array
        are the mean of the neighbouring pixels/voxels, where the neighbourhood
        is defined by `factor`.

        Parameters
        ----------
        factor: int
            factor by which the size of the image should be reduced along
            the y and x axis

        Returns
        -------
        tmlib.image.Image
            shrunken image
        '''
        shrink_factors = (factor,) * 2 + (1,) * (self._array.ndim - 2)
        arr = skimage.measure.block_reduce(
                self._array, shrink_factors, func=np.mean
        ).astype(self.dtype)
        return self.__class__(arr, self.metadata)

    def align(self, crop=True):
        '''Aligns, i.e. shifts and optionally crops, an image based on
        pre-calculated shift and overhang values.

        Parameters
        ----------
        crop: bool, optional
            whether image should be cropped or rather padded
            with zero values (default: ``True``)

        Returns
        -------
        tmlib.image.Image
            aligned image

        Warning
        -------
        Alignment may change the dimensions of the image when `crop` is
        ``True``.
        '''
        if self.metadata is None:
            raise AttributeError(
                'Image requires attribute "metadata" for alignment.'
            )
        md = self.metadata
        # The shape of the arrays may change when cropped
        arrays = list()
        for z, pixels in self.iter_planes():
            arr = image_utils.shift_and_crop(
                pixels.array, y=md.y_shift, x=md.x_shift,
                bottom=md.upper_overhang, top=md.lower_overhang,
                right=md.left_overhang, left=md.right_overhang, crop=crop
            )
            arrays.append(arr)
        arr = np.dstack(arrays)
        new_object = self.__class__(arr, self.metadata)
        new_object.metadata.is_aligned = True
        return new_object


class ChannelImage(Image):

    '''Class for a channel image: a grayscale image with a single band.'''

    @assert_type(metadata=['tmlib.metadata.ChannelImageMetadata', 'types.NoneType'])
    def __init__(self, array, metadata=None):
        '''
        Parameters
        ----------
        array: numpy.ndarray[uint16]
            pixels/voxels array
        metadata: tmlib.metadata.ChannelImageMetadata, optional
            image metadata (default: ``None``)
        '''
        super(ChannelImage, self).__init__(array, metadata)
        if not self.is_uint:
            raise TypeError('Image must have unsigned integer type.')

    @classmethod
    def create_as_background(cls, y_dimension, x_dimension, z_dimension,
                             metadata=None, add_noise=False,
                             mu=None, sigma=None):
        '''Creates an image with background voxels. By default background will
        be zero values. Optionally, Gaussian noise can be added to simulate
        camera background.

        Parameters
        ----------
        y_dimension: int
            length of the array along the y-axis
        x_dimension: int
            length of the array along the x-axis
        z_dimension: int
            length of the array along the z-axis
        metadata: tmlib.metadata.ImageMetadata, optional
            image metadata (default: ``None``)
        add_noise: bool, optional
            add Gaussian noise (default: ``False``)
        noise_mu: int, optional
            mean of background noise (default: ``None``)
        noise_sigma: int, optional
            variance of background noise (default: ``None``)

        Returns
        -------
        tmlib.image.ChannelImage
            image with background values
        '''
        dims = (z_dimension, y_dimension, x_dimension)
        if add_noise:
            if mu is None or sigma is None:
                raise ValueError(
                    'Arguments "mu" and "sigma" are required '
                    'when argument "add_noise" is set to True.'
                )
            arr = np.random.normal(mu, sigma, np.prod(dims)).astype(np.uint16)
        else:
            arr = np.zeros(dims, dtype=np.uint16)
        return cls(arr, self.metadata)

    def project(self, func=np.max, axis='z'):
        '''Performs a projection of the array along a given `axis` and using
        a given function.

        Parameters
        ----------
        func: function, optional
            function that should be used for the projection
            (default: ``numpy.max``)
        axis: str, optional
            axis along which the image array should be projected
            (default: ``"z"``)
        '''
        axis_map = {'y': 0, 'x': 1, 'z': 2}
        arr = func(self._array, axis=axis_map[axis])
        return self.__class__(arr, self.metadata)

    def scale(self, lower, upper):
        '''Scales values to 8-bit such that the range [`lower`, `upper`]
        will be mapped to the range [0, 255].

        Parameters
        ----------
        lower: int
            value below which pixel values will be set to 0
        upper: int
            value above which pixel values will be set to 255

        Returns
        -------
        tmlib.image.Image
            image with rescaled voxels
        '''
        if self.is_uint16:
            arr = image_utils.map_to_uint8(self._array, lower, upper)
            self.metadata.is_rescaled = True
            return self.__class__(arr, self.metadata)
        elif self.is_uint8:
            return self
        else:
            TypeError(
                'Only voxels with unsigned integer type can be scaled.'
            )

    def clip(self, lower, upper):
        '''Clips intensity values below `lower` and above `upper`, i.e. set all
        pixel values below `lower` to `lower` and all above `upper` to `upper`.

        Parameters
        ----------
        lower: int
            value below which pixel values should be clippe
        upper: int
            value above which pixel values should be clipped

        Returns
        -------
        tmlib.image.ChannelImage
            image with clipped voxels
        '''
        arr = np.clip(self._array, lower, upper)
        return ChannelImage(arr, self.metadata)

    @assert_type(stats='tmlib.image.IllumstatsContainer')
    def correct(self, stats):
        '''Corrects the image for illumination artifacts.

        Parameters
        ----------
        stats: tmlib.image.IllumstatsContainer
            mean and standard deviation statistics at each pixel position
            calculated over all images of the same channel

        Returns
        -------
        tmlib.image.ChannelImage
            image with voxels corrected for illumination

        Raises
        ------
        ValueError
            when channel doesn't match between illumination statistics and
            image
        '''
        if self.metadata is None:
            raise ValueError('Illumination correction requires image metadata.')
        if (stats.mean.metadata.channel != self.metadata.channel or
                stats.std.metadata.channel != self.metadata.channel):
            raise ValueError('Channel indices must match.')
        arr = np.zeros(self.dimensions, dtype=self.dtype)
        for z, pixels in self.iter_planes():
            arr[:, :, z, ...] = image_utils.correct_illumination(
                pixels.array, stats.mean.array, stats.std.array
            )
        new_object = ChannelImage(arr, self.metadata)
        if self.metadata is not None:
            new_object.metadata.is_corrected = True
        return new_object


class PyramidTile(Image):

    '''Class for a pyramid tile: an image with a single z-level and
    y, x dimensions of 256 x 256 voxels.
    '''

    TILE_SIZE = 256

    @assert_type(
        metadata=['tmlib.metadata.PyramidTileMetadata', 'types.NoneType']
    )
    def __init__(self, array, metadata=None):
        '''
        Parameters
        ----------
        array: numpy.ndarray[uint8]
            2D pixel plane
        metadata: tmlib.metadata.PyramidTileMetadata, optional
            image metadata (default: ``None``)
        '''
        super(PyramidTile, self).__init__(array, metadata)
        if self.dimensions[2] > 1:
            raise ValueError('Image must be two-dimensional.')
        if not self.is_uint8:
            raise TypeError(
                'Image must have 8-bit unsigned integer data type.'
            )
        if any([d > self.TILE_SIZE or d == 0 for d in self.array.shape]):
            raise ValueError(
                'Height and width of image must be greater than zero and '
                'maximally %d pixels.' % self.TILE_SIZE
            )

    @classmethod
    def create_as_background(cls, metadata=None, add_noise=False, mu=None, sigma=None):
        '''Create an image with background voxels. By default background will
        be zero values. Optionally, Gaussian noise can be added to simulate
        camera background.

        Parameters
        ----------
        metadata: tmlib.metadata.ImageMetadata, optional
            image metadata (default: ``None``)
        add_noise: bool, optional
            add Gaussian noise (default: ``False``)
        noise_mu: int, optional
            mean of background noise (default: ``None``)
        noise_sigma: int, optional
            variance of background noise (default: ``None``)

        Returns
        -------
        tmlib.image.PyramidTile
            image with background pixel values
        '''
        if add_noise:
            if mu is None or sigma is None:
                raise ValueError(
                    'Arguments "mu" and "sigma" are required '
                    'when argument "add_noise" is set to True.'
                )
            arr = np.random.normal(mu, sigma, self._tile_size**2).astype(np.uint8)
        else:
            arr = np.zeros((cls.TILE_SIZE,) * 2, dtype=np.uint8)
        return cls(arr, metadata)

    def jpeg_encode(self, quality=95):
        '''Encodes the image as a JPEG buffer object.

        Parameters
        ----------
        quality: int, optional
            JPEG quality from 0 to 100 (default: ``95``)

        Returns
        -------
        numpy.ndarray

        Examples
        --------
        >>>img = PyramidTile.create_as_background()
        >>>buf = img.jpeg_encode()
        >>>with open('myfile.jpeg', 'w') as f:
        >>>    f.write(buf)
        '''
        return cv2.imencode(
            '.jpeg', self.array, [cv2.IMWRITE_JPEG_QUALITY, quality]
        )

class BrightfieldImage(Image):

    '''Class for a brightfield image: a 3D RGB image with three bands
    and voxels with 8-bit unsigned integer type.
    '''

    def __init__(self, pixels, metadata=None):
        '''
        Parameters
        ----------
        pixels: numpy.ndarray[uint8]
            pixel plane
        metadata: tmlib.metadata.ImageMetadata, optional
            image metadata (default: ``None``)
        '''
        super(BrightfieldImage, self).__init__(pixel, metadata, is_color=True)
        if self.dtype != np.uint8:
            raise TypeError(
                'Image must have 8-bit unsigned integer data type.'
            )
        if self.dimensions[2] != 3:
            raise ValueError('Image must be RGB.')

    def split_bands(self, separation_mat=skimage.color.hed_from_rgb):
        '''Split different colors of a immunohistochemistry stain
        into separate channels based on
        Ruifrok and Johnston's color deconvolution method [1]_.

        Parameters
        ----------
        separation_mat: numpy.ndarray
            stain separation matrix as available in
            :py:mod:`skimage.color`, for information on how to create custom
            matrices see G. Landini's description for the corresponding
            `Fiji plugin <http://www.mecourse.com/landinig/software/cdeconv/cdeconv.html>`_
            (default: :py:attr:`skimage.color.hed_from_rgb`)

        Returns
        -------
        Tuple[tmlib.image.ChannelImage]
            separate channel image for each band

        References
        ----------
        .. _[1]: Ruifrok AC, Johnston DA. Quantification of histochemical staining by color deconvolution. Anal Quant Cytol Histol 23: 291-299, 2001
        '''
        # TODO: metadata for brightfield images
        arr = skimage.color.separate_stains(self.array, separation_mat)
        channel_img_1 = ChannelImage(arr[:, :, 1], self.metadata)
        channel_img_2 = ChannelImage(arr[:, :, 2], self.metadata)
        channel_img_3 = ChannelImage(arr[:, :, 3], self.metadata)
        return (channel_img_1, channel_img_2, channel_img_3)


class ProbabilityImage(Image):

    '''Class for a probability image: a greyscale image with a single band.

    Note
    ----
    Despite its name, pixel values are represented by 16-bit unsigned integers
    rather than floats in the range [0, 1].
    '''

    @assert_type(
        metadata=['tmlib.metadata.ProbabilityImageMetadata', 'types.NoneType']
    )
    def __init__(self, array, metadata=None):
        '''
        Parameters
        ----------
        array: numpy.ndarray[uint16]
            pixels/voxels array
        metadata: tmlib.metadata.ProbabilityImageMetadata, optional
            image metadata (default: ``None``)
        '''
        super(ChannelImage, self).__init__(array, metadata)
        if not self.is_uint16:
            raise TypeError(
                'Image must have 16-bit unsigned integer type.'
            )
        if self.dimensions[2] != 1:
            raise ValueError('Image must be grayscale.')


class IllumstatsImage(Image):

    '''Class for a statistics image: a 2D greyscale image with a
    single band and data type float.
    '''

    @assert_type(
        metadata=['tmlib.metadata.IllumstatsImageMetadata', 'types.NoneType']
    )
    def __init__(self, array, metadata=None):
        '''
        Parameters
        ----------
        array: numpy.ndarray[float]
            2D pixels array
        metadata: tmlib.metadata.IllumstatsImageMetadata
            metadata (default: ``None``)
        '''
        super(IllumstatsImage, self).__init__(array, metadata)
        if self.dimensions[2] != 1:
            raise ValueError('Image must be two-dimensional.')
        if not self.is_float:
            raise TypeError('Image must have data type float.')


class IllumstatsContainer(object):

    '''Class that serves as a container for illumination statistics images.

    It provides the mean and standard deviation matrices for a given
    channel. The statistics are calculated at each pixel position over all
    sites acquired in the same channel [1]_.

    References
    ----------
    .. [1] Stoeger T, Battich N, Herrmann MD, Yakimovich Y, Pelkmans L. 2015.
           Computer vision for image-based transcriptomics. Methods.
    '''

    @assert_type(
        mean='tmlib.image.IllumstatsImage', std='tmlib.image.IllumstatsImage'
    )
    def __init__(self, mean, std, percentiles):
        '''
        Parameters
        ----------
        mean: tmlib.image.IllumstatsImage
            matrix of mean values calculated over all sites
        std: tmlib.image.IllumstatsImage
            matrix of standard deviation values calculated over all sites
        percentiles: Dict[float, int]
            intensity percentiles over all sites
        '''
        self.mean = mean
        self.std = std
        self.percentiles = percentiles

    def smooth(self, sigma=5):
        '''Smooth mean and standard deviation statistic matrices with a
        Gaussian filter. This is useful to prevent outliers voxels with
        extreme values to introduce artifacts into the image upon correction.

        Parameters
        ----------
        sigma: int, optional
            size of the standard deviation of the Gaussian kernel
            (default: ``5``)

        Note
        ----
        `mean` and `std` are modified in place.
        '''
        self.mean.array = self.mean.smooth(sigma).array
        self.mean.metadata.is_smoothed = True
        self.std.array = self.std.smooth(sigma).array
        self.std.metadata.is_smoothed = True
        return self

    def get_closest_percentile(self, value):
        '''Obtains the value for the percentile closest to a given value.

        Parameters
        ----------
        value: int or float
            approximate percentile value

        Returns
        -------
        int
        '''
        keys = np.array(self.percentiles.keys())
        idx = np.abs(keys - value).argmin()
        return self.percentiles[keys[idx]]


