import numpy as np
import logging
from gi.repository import Vips
from abc import ABCMeta
from abc import abstractmethod
from . import image_utils
from .errors import MetadataError

logger = logging.getLogger(__name__)


class StichedImage(object):

    '''
    Abstract base class for an image that was created by stitching several
    smaller images together.
    '''

    __metaclass__ = ABCMeta

    def __init__(self, array):
        '''
        Instantiate an instance of class Mosaic.

        Parameters
        ----------
        array: Vips.Image
            stitched image pixel array
        '''
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

    @abstractmethod
    def _build_image_grid(images):
        pass

    @abstractmethod
    def create_from_images(images, dx=0, dy=0, stats=None, shift=None):
        pass


class Mosaic(StichedImage):

    '''
    Class for a mosaic image of type `Vips.Image`.
    '''

    def __init__(self, array):
        '''
        Instantiate an instance of class Mosaic.

        Parameters
        ----------
        array: Vips.Image
            stitched image pixel array
        '''
        super(Mosaic, self).__init__(array)
        self.array = array

    @staticmethod
    def _build_image_grid(images):
        coordinates = [im.metadata.grid_coordinates for im in images]
        height, width = np.max(coordinates, axis=0)  # zero-based
        grid = np.empty((height+1, width+1), dtype=object)
        for i, c in enumerate(coordinates):
            grid[c[0], c[1]] = images[i]
        return grid

    @staticmethod
    def create_from_images(images, dx=0, dy=0, stats=None, shift=None):
        '''
        Create a Mosaic object from image objects.

        Parameters
        ----------
        images: List[ChannelImage]
            set of images that are all of the same *cycle* and *channel*
        dx: int, optional
            displacement in x direction in pixels; i.e. overlap of images
            in x direction (negative integer value; default: ``0``)
        dy: int, optional
            displacement in y direction in pixels; i.e. overlap of images
            in y direction (negative integer value; default: ``0``)
        stats: IllumstatsImages, optional
            illumination statistics to correct images for
            illumination artifacts
        shift: List[ShiftDescription], optional
            shift descriptions, when provided images are aligned between
            cycles

        Returns
        -------
        Mosaic

        Raises
        ------
        ValueError
            when `dx` or `dy` are positive
        MetadataError
            when `images` are not of same *cycle* or *channel*
        '''
        if not isinstance(dx, int) or dx > 0:
            raise ValueError('"dx" has to be a negative integer value')
        if not isinstance(dy, int) or dy > 0:
            raise ValueError('"dy" has to be a negative integer value')

        cycles = set([im.metadata.cycle for im in images])
        if len(cycles) > 1:
            raise MetadataError('All images must be of the same cycle')
        channels = set([im.metadata.channel for im in images])
        if len(channels) > 1:
            raise MetadataError('All images must be of the same channel')

        grid = Mosaic._build_image_grid(images)
        rows = list()
        for i in xrange(grid.shape[0]):
            current_row = list()
            for j in xrange(grid.shape[1]):
                img = grid[i, j]
                if stats:
                    img = img.correct(stats)
                if shift:
                    img = img.align(crop=False)
                current_row.append(img.pixels.array)
            rows.append(reduce(lambda x, y:
                        x.merge(y, 'horizontal', -x.width-dx, 0), current_row))
        img = reduce(lambda x, y:
                     x.merge(y, 'vertical', 0, -x.height-dy), rows)

        return Mosaic(img)


class Collage(StichedImage):

    def __init__(self, array):
        '''
        Instantiate an instance of class Mosaic.

        Parameters
        ----------
        array: Vips.Image
            stitched image pixel array
        '''
        super(Collage, self).__init__(array)
        self.array = array

    @staticmethod
    def _build_image_grid(images):
        # Build a quadratic grid and place the images in there without any
        # particular order
        dim = int(np.ceil(len(images) / 2))
        grid = np.empty((dim, dim), dtype=object)
        count = -1
        for i in xrange(dim):
            for j in xrange(dim):
                count += 1
                if count < len(images):
                    grid[i, j] = images[count]
        return grid

    @staticmethod
    def create_from_images(images, dx=100, dy=100, stats=None, shift=None):
        '''
        Create a Collage object from image objects.

        Parameters
        ----------
        images: List[ChannelImage]
            set of images that are all of the same *cycle* and *channel*
        dx: int, optional
            displacement in x direction in pixels, i.e. gap that should be
            introduced between individual images in x direction
            (positive integer value; default: ``100``)
        dy: int, optional
            displacement in y direction in pixels, i.e. gap that should be
            introduced between individual images in y direction
            (positive integer value; default: ``100``)
        stats: IllumstatsImages, optional
            illumination statistics to correct images for
            illumination artifacts
        shift: List[ShiftDescription], optional
            shift descriptions, when provided images are aligned between
            cycles

        Returns
        -------
        Mosaic

        Raises
        ------
        ValueError
            when `dx` or `dy` are negative
        MetadataError
            when `images` are not of same *cycle* or *channel*
        TypeError
            when `images` are not of the same data type
        '''
        if not isinstance(dx, int) or dx < 0:
            raise ValueError('"dx" has to be a positive integer value')
        if not isinstance(dy, int) or dy < 0:
            raise ValueError('"dy" has to be a positive integer value')

        cycles = set([im.metadata.cycle for im in images])
        if len(cycles) > 1:
            raise MetadataError('All images must be of the same cycle')
        channels = set([im.metadata.channel for im in images])
        if len(channels) > 1:
            raise MetadataError('All images must be of the same channel')
        dtypes = np.unique([im.pixels.dtype for im in images])
        if len(dtypes) > 1:
            raise TypeError('All images must have the same type')

        image_dims = np.array([im.pixels.dimensions for im in images])

        grid = Collage._build_image_grid(images)

        im_height = np.max(image_dims[:, 0])
        im_width = np.max(image_dims[:, 1])
        im_dtype = dtypes[0]
        column_spacer = image_utils.create_spacer_image(
                im_height, dx, dtype=im_dtype, bands=1)
        row_spacer = image_utils.create_spacer_image(
                dy,
                im_width*grid.shape[1] +
                column_spacer.width*(grid.shape[1]-1),
                dtype=im_dtype, bands=1)

        rows = list()
        for i in xrange(grid.shape[0]):
            current_row = list()
            for j in xrange(grid.shape[1]):
                img = grid[i, j]
                if stats:
                    img = img.correct(stats)
                if shift:
                    img = img.align(crop=False)
                # pad image with zeros if necessary
                height_diff = im_height - img.pixels.dimensions[0]
                if height_diff > 0:
                    top = int(np.floor((height_diff) / 2))
                else:
                    top = 0
                width_diff = im_width - img.pixels.dimensions[1]
                if width_diff > 0:
                    left = int(np.floor((width_diff) / 2))
                else:
                    left = 0
                empty_image = image_utils.create_spacer_image(
                                im_height, im_width,
                                dtype=img.pixels.dtype, bands=1)
                padded_image = empty_image.insert(
                                img.pixels.array, left, top)

                current_row.append(padded_image)
                if j != grid.shape[1]:
                    current_row.append(column_spacer)

            rows.append(reduce(lambda x, y:
                        x.merge(y, 'horizontal', -x.width-dx, 0), current_row))
            if i != grid.shape[0]:
                rows.append(row_spacer)

        img = reduce(lambda x, y:
                     x.merge(y, 'vertical', 0, -x.height-dy), rows)

        return Collage(img)
