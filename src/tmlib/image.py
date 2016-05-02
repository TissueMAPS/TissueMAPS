import os
import numpy as np
import scipy.ndimage as ndi
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
    '''
    Check if filename ends with a supported file extension.

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
    Abstract base class for an image, which represents a 2D pixels array.

    2D means that there is only one *z* resolution.
    However, the pixels array may still have more than 2 dimensions.
    The 3rd dimension represents color and is referred to as "bands".

    The class provides the pixel array as well as associated metadata.
    It makes use of lazy loading so that image objects can be created and their
    metadata attribute accessed without the pixels arrays being immediately
    loaded into memory.
    '''

    # TODO: make methods more general to work with 3D arrays to handle multiple
    # bands

    __metaclass__ = ABCMeta

    @assert_type(pixels='numpy.ndarray')
    def __init__(self, pixels, metadata=None):
        '''
        Parameters
        ----------
        pixels: numpy.ndarray
            pixels array
        metadata: tmlib.metadata.ImageMetadata, optional
            image metadata (default: ``None``)
        '''
        self.pixels = pixels
        self.metadata = metadata

    @property
    def dimensions(self):
        '''Tuple[int]: y, x dimensions of the pixel array'''
        return self.pixels.shape[0:2]

    @property
    def bands(self):
        '''int: number of colors encoded in the pixels array'''
        if len(self.pixels.shape) > 2:
            return self.pixels.shape[2]
        else:
            return 1

    @property
    def dtype(self):
        '''str: data type of the pixel array elements'''
        return self.pixels.dtype

    @property
    def is_float(self):
        '''bool: whether pixel array has float data type
        '''
        return self.dtype == np.float

    @property
    def is_uint(self):
        '''bool: whether pixel array has unsigned integer data type'''
        return self.dtype == np.uint16 or self.dtype == np.uint8

    @property
    def is_uint8(self):
        '''bool: whether pixel array has 8-bit unsigned integer data type'''
        return self.dtype == np.uint8

    @property
    def is_uint16(self):
        '''bool: whether pixel array has 16-bit unsigned integer data type'''
        return self.dtype == np.uint16

    @property
    def is_binary(self):
        '''bool: whether pixel array has boolean data type'''
        return self.dtype == np.bool

    def extract(self, y_offset, x_offset, height, width):
        '''Extract a continuous, rectangular area of pixels from the image.

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
        tmlib.image.Image
            extracted pixels with dimensions `height` x `width`
        '''
        pxls = self.pixels[
            y_offset:(y_offset+height), x_offset:(x_offset+width)
        ]
        return self.__class__(pxls, self.metadata)

    @assert_type(image='tmlib.image.Image')
    def insert(self, image, y_offset, x_offset, inplace=True):
        '''Insert a continuous, rectangular area of pixels into an image.

        Parameters
        ----------
        image: tmlib.image.Image
            image whose pixels should be inserted
        y_offset: int
            index of the top, left point of the rectangle on the *y* axis
        x_offset: int
            index of the top, left point of the rectangle on the *x* axis
        inplace: bool, optional
            insert pixels into the existing image rather than into a copy
            (default: ``True``)

        Returns
        -------
        tmlib.image.Image
            image with inserted pixels
        '''
        if (image.dimensions[0] + y_offset > self.dimensions[0] or
                image.dimensions[1] + x_offset > self.dimensions[1]):
            raise ValueError('Image doesn\'t fit.')
        if inplace:
            pxls = self.pixels
        else:
            pxls = self.pixels.copy()
        h, w = image.dimensions
        pxls[y_offset:(y_offset+h), x_offset:(x_offset+w)] = image.pixels
        if inplace:
            return self
        else:
            return self.__class__(pxls, self.metadata)

    @assert_type(image='tmlib.image.Image')
    def merge(self, image, direction, offset, inplace=True):
        '''Merge pixels arrays of two images into one.

        Parameters
        ----------
        image: tmlib.image.Image
            image object whose pixels should used for merging
        direction: str
            direction along which the two pixels arrays should be merged,
            either ``"horizontal"`` or ``"vertical"``
        offset: int
            offset for `image` in the existing object
        inplace: bool, optional
            merge pixels into the existing image rather than into a copy
            (default: ``True``)

        Parameters
        ----------
        tmlib.image.Image
            image with rescaled pixels
        '''
        if inplace:
            pxls = self.pixels
        else:
            pxls = self.pixels.copy()
        if direction == 'vertical':
            pxls[offset:, :] = image.pixels[offset:, :]
        elif direction == 'horizontal':
            pxls[:, offset:] = image.pixels[:, offset:]
        else:
            raise ValueError(
                'Argument "direction" must be either '
                '"horizontal" or "vertical"'
            )
        if inplace:
            return self
        else:
            return self.__class__(pxls, self.metadata)

    @assert_type(image='tmlib.image.Image')
    def join(self, image, direction):
        '''Join two pixels arrays.

        Parameters
        ----------
        image: tmlib.image.Image
            image object whose pixels should used for joining
        direction: str
            direction along which the two pixels arrays should be joined,
            either ``"horizontal"`` or ``"vertical"``

        Returns
        -------
        tmlib.image.Image
            image with joined pixels
        '''
        if direction == 'vertical':
            pxls = np.vstack([self.pixels, image.pixels])
        elif direction == 'horizontal':
            pxls = np.hstack([self.pixels, image.pixels])
        else:
            raise ValueError(
                'Argument "direction" must be either '
                '"horizontal" or "vertical"'
            )
        return self.__class__(pxls, self.metadata)

    def pad_with_background(self, n, side):
        '''Pad one side of the pixels array with zero value pixels.

        Parameters
        ----------
        n: int
            number of pixels that should be added along the given axis
        side: str
            side of the array that should be padded;
            either ``"top"``, ``"bottom"``, ``"left"``, or ``"right"``

        Returns
        -------
        tmlib.image.Image
            image with clipped pixels
        '''
        if side == 'top':
            pxls = np.zeros((n, self.dimensions[1]), dtype=self.dtype)
            pxls = np.vstack([pxls, self.pixels])
        elif side == 'bottom':
            pxls = np.zeros((n, self.dimensions[1]), dtype=self.dtype)
            pxls = np.vstack([self.pixels, pxls])
        elif side == 'left':
            pxls = np.zeros((self.dimensions[0], n), dtype=self.dtype)
            pxls = np.hstack([pxls, self.pixels])
        elif side == 'right':
            pxls = np.zeros((self.dimensions[0], n), dtype=self.dtype)
            pxls = np.hstack([self.pixels, pxls])
        else:
            raise ValueError(
                'Argument "side" must be one of the following: '
                '"top", "bottom", "left", "right"'
            )
        return self.__class__(pxls, self.metadata)

    def shrink(self, factor):
        '''Reduce the size of the pixels array.

        Parameters
        ----------
        factor: int
            factor by which the size of the pixels array should be reduced

        Returns
        -------
        tmlib.image.Image
            image with shrunken pixels
        '''
        pxls = skimage.measure.block_reduce(
            self.pixels, (factor, factor), func=np.mean
        ).astype(self.dtype)
        return self.__class__(pxls, self.metadata)

    def align(self, crop=True):
        '''Align, i.e. shift and crop, an image based on pre-calculated shift
        and overhang values.

        Parameters
        ----------
        crop: bool, optional
            whether images should cropped or rather padded
            with zero valued pixels (default: ``True``)

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
        pxls = image_utils.shift_and_crop(
            self.pixels, y=md.y_shift, x=md.x_shift,
            bottom=md.upper_overhang, top=md.lower_overhang,
            right=md.left_overhang, left=md.right_overhang, crop=crop
        )
        new_object = self.__class__(pxls, self.metadata)
        new_object.metadata.is_aligned = True
        return new_object


class ChannelImage(Image):

    '''Class for a channel image: a 2D greyscale image with a single band.
    '''

    @assert_type(metadata=['tmlib.metadata.ChannelImageMetadata', 'types.NoneType'])
    def __init__(self, pixels, metadata=None):
        '''
        Parameters
        ----------
        pixels: numpy.ndarray[uint16]
            pixels array
        metadata: tmlib.metadata.ChannelImageMetadata, optional
            image metadata (default: ``None``)
        '''
        super(ChannelImage, self).__init__(pixels, metadata)
        if not self.is_uint:
            raise TypeError(
                'Argument "pixels" must have unsigned integer type.'
            )
        if self.bands != 1:
            raise ValueError('Argument "pixels" must be grayscale.')

    @staticmethod
    def create_as_background(y_dimension, x_dimension,
                             metadata=None, add_noise=False,
                             mu=None, sigma=None):
        '''Create an image with background pixels. By default background will
        be zero values. Optionally, Gaussian noise can be added to simulate
        camera background.

        Parameters
        ----------
        y_dimension: int
            length of the array along the y-axis
        x_dimension: int
            length of the array along the x-axis
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
            image with background pixels
        '''
        if add_noise:
            if mu is None or sigma is None:
                raise ValueError(
                    'Arguments "mu" and "sigma" are required '
                    'when argument "add_noise" is set to True.'
                )
            pxls = np.random.normal(
                mu, sigma, y_dimension * x_dimension
            ).astype(np.uint16)
        else:
            pxls = np.zeros((y_dimension, x_dimension), dtype=np.uint16)
        return ChannelImage(pxls, metadata)

    def scale(self, lower, upper):
        '''Scale pixel values to 8-bit such that the range [`lower`, `upper`]
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
            image with rescaled pixels
        '''
        if self.is_uint16:
            pxls = image_utils.map_to_uint8(self.pixels, lower, upper)
            return self.__class__(pxls, self.metadata)
        elif self.is_uint8:
            return self
        else:
            TypeError(
                'Only pixels with unsigned integer type can be scaled.'
            )

    def clip(self, lower, upper):
        '''Clip intensity values below `lower` and above `upper`, i.e. set all
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
            image with clipped pixels
        '''
        pxls = np.clip(self.pixels, lower, upper)
        return ChannelImage(pxls, self.metadata)

    def smooth(self, sigma):
        '''Apply a Gaussian smoothing filter to the pixels array.

        Parameters
        ----------
        sigma: int
            size of the standard deviation of the Gaussian kernel

        Returns
        -------
        tmlib.image.ChannelImage
            image with smoothed pixels
        '''
        pxls = ndi.filters.gaussian_filter(self.pixels, sigma)
        return ChannelImage(pxls, self.metadata)

    def correct(self, stats):
        '''Correct image for illumination artifacts.

        Parameters
        ----------
        stats: tmlib.image.IllumstatsImages
            mean and standard deviation statistics at each pixel position
            calculated over all images of the same channel

        Returns
        -------
        tmlib.image.ChannelImage
            image with pixels corrected for illumination

        Raises
        ------
        ValueError
            when channel doesn't match between illumination statistics and
            image
        '''
        if self.metadata is not None:
            if (stats.mean.metadata.channel != self.metadata.channel or
                    stats.std.metadata.channel != self.metadata.channel):
                raise ValueError('Channel indices must match.')
        else:
            logger.warn('no image metadata provided')
        pxls = image_utils.correct_illumination(
            self.pixels, stats.mean.pixels, stats.std.pixels
        )
        new_object = ChannelImage(pxls, self.metadata)
        if self.metadata is not None:
            new_object.metadata.is_corrected = True
        return new_object


class PyramidTile(Image):

    '''Class for a pyramid tile: a 2D image with maximal dimensions 256x256.
    '''

    @assert_type(
        metadata=['tmlib.metadata.PyramidTileMetadata', 'types.NoneType']
    )
    def __init__(self, pixels, metadata=None):
        '''
        Parameters
        ----------
        pixels: numpy.ndarray[uint8]
            pixels array
        metadata: tmlib.metadata.PyramidTileMetadata, optional
            image metadata (default: ``None``)
        '''
        super(PyramidTile, self).__init__(pixels, metadata)
        if not self.is_uint8:
            raise TypeError(
                'Pixels must have 8-bit unsigned integer data type.'
            )
        if any([d > 256 for d in self.dimensions]):
            raise ValueError(
                'Length of "pixels" axis can be maximally 256 pixels.'
            )

    @staticmethod
    def create_as_background(metadata=None, add_noise=False,
                             mu=None, sigma=None):
        '''Create an image with background pixels. By default background will
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
            image with background pixels
        '''
        if add_noise:
            if mu is None or sigma is None:
                raise ValueError(
                    'Arguments "mu" and "sigma" are required '
                    'when argument "add_noise" is set to True.'
                )
            pxls = np.random.normal(mu, sigma, 256 * 256).astype(np.uint8)
        else:
            pxls = np.zeros((256, 256), dtype=np.uint8)
        return PyramidTile(pxls, metadata)


class LabelImage(Image):

    '''Class for a labeled image: a 2D grayscale image with one band where
    pixels of each connected component (segmented object) have a unique integer
    value.
    '''

    def __init__(self, pixels, metadata=None):
        '''
        Parameters
        ----------
        pixels: numpy.ndarray[int32]
            pixels array
        metadata: tmlib.metadata.ImageMetadata, optional
            image metadata (default: ``None``)
        '''
        super(LabelImage, self).__init__(pixels, metadata)
        if self.dtype != 'int32':
            raise TypeError(
                    'Argument "pixels" must have data type int32.')
        if self.bands != 1:
            raise ValueError('Argument "pixels" must be grayscale.')

    def get_outlines(self, keep_ids=False):
        '''Obtain the outlines of objects (labeled connected components) in the
        image.

        Parameters
        ----------
        keep_ids: bool, optional
            whether the ids (pixel values) of objects should be preserved;
            returns unsigned integer type if ``True`` and binary type otherwise
            (default: ``False``)

        Returns
        -------
        numpy.ndarray
            pixels array
        '''
        return image_utils.compute_outlines(self.pixels, keep_ids)

    @property
    def n_objects(self):
        '''int: number of objects (labeled connected components) in the image
        '''
        return len(np.unique(self.pixels[self.pixels > 0]))

    def remove_objects(self, ids):
        '''Remove certain objects from the image.

        Parameters
        ----------
        ids: List[int]
            IDs of objects that should be removed

        Returns
        -------
        numpy.ndarray
            pixels array
        '''
        return image_utils.remove_objects(self.pixels, ids)


class BrightfieldImage(Image):

    '''Class for a brightfield image: a 2D RGB image with three bands
    and pixels with 8-bit unsigned integer type.
    '''

    def __init__(self, pixels, metadata=None):
        '''
        Parameters
        ----------
        pixels: numpy.ndarray[uint8]
            pixels array
        metadata: tmlib.metadata.ImageMetadata, optional
            image metadata (default: ``None``)
        '''
        super(BrightfieldImage, self).__init__(pixels, metadata)
        if pixels is not None:
            if self.dtype != np.uint8:
                raise TypeError(
                        'Argument "pixels" must have 8-bit unsigned integer '
                        'data type.')
            if self.bands != 3:
                raise ValueError(
                        'Argument "pixels" must be a three-dimensional array '
                        'with 3 bands.')

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
        pxls = skimage.color.separate_stains(self.pixels, separation_mat)
        channel_img_1 = ChannelImage(pxls[:, :, 1], self.metadata)
        channel_img_2 = ChannelImage(pxls[:, :, 2], self.metadata)
        channel_img_3 = ChannelImage(pxls[:, :, 3], self.metadata)
        return (channel_img_1, channel_img_2, channel_img_3)


class ProbabilityImage(Image):

    '''Class for a probability image: a 2D greyscale image with a single band.

    Note
    ----
    Despite its name, pixel values are represented by 16-bit unsigned integers
    rather than floats in the range [0, 1]. 
    '''

    @assert_type(
        metadata=['tmlib.metadata.ProbabilityImageMetadata', 'types.NoneType']
    )
    def __init__(self, pixels, metadata=None):
        '''
        Parameters
        ----------
        pixels: numpy.ndarray[uint16]
            pixels array
        metadata: tmlib.metadata.ProbabilityImageMetadata, optional
            image metadata (default: ``None``)
        '''
        super(ChannelImage, self).__init__(pixels, metadata)
        if not self.is_uint16:
            raise TypeError(
                'Argument "pixels" must have 16-bit unsigned integer type.'
            )
        if self.bands != 1:
            raise ValueError('Argument "pixels" must be grayscale.')


class IllumstatsImage(Image):

    '''Class for a statistics image: a 2D greyscale image with a
    single band and data type float.
    '''

    @assert_type(
        metadata=['tmlib.metadata.IllumstatsImageMetadata', 'types.NoneType']
    )
    def __init__(self, pixels, metadata=None):
        '''
        Parameters
        ----------
        pixels: numpy.ndarray[float]
            pixels array
        metadata: tmlib.metadata.IllumstatsImageMetadata
            metadata (default: ``None``)
        '''
        super(IllumstatsImage, self).__init__(pixels, metadata)
        if self.bands != 1:
            raise ValueError(
                'Argument "pixels" must have a single band.'
            )
        if not self.is_float:
            raise TypeError(
                'Argument "pixels" must have data type float.'
            )

    def smooth(self, sigma):
        '''Apply a Gaussian smoothing filter to the pixels array.

        Parameters
        ----------
        sigma: int
            size of the standard deviation of the Gaussian kernel

        Returns
        -------
        tmlib.image.IllumstatsImage
            image with smoothed pixels
        '''
        pxls = ndi.filters.gaussian_filter(self.pixels, sigma)
        return IllumstatsImage(pxls, self.metadata)


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
        Gaussian filter. This is useful to prevent outliers pixels with
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
        self.mean.pixels = self.mean.smooth(sigma).pixels
        self.mean.metadata.is_smoothed = True
        self.std.pixels = self.std.smooth(sigma).pixels
        self.std.metadata.is_smoothed = True
        return self
