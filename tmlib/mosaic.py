import numpy as np
from gi.repository import Vips
from ..errors import MetadataError


class Mosaic(object):

    '''
    Class for a mosaic image of type `Vips.Image`.
    '''

    def __init__(self, array):
        '''
        Initialize an instance of class Mosaic.

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

    @staticmethod
    def _build_image_grid(images):
        coordinates = [im.metadata.coordinates for im in images]
        height, width = np.max(coordinates, axis=0)
        grid = np.empty((height, width))
        for i, c in enumerate(coordinates):
            grid[c[0], c[1]] = images[i]
        return grid

    @staticmethod
    def create_from_images(images, dx, dy, stats=None):
        '''
        Create a Mosaic object from image objects.

        Parameters
        ----------
        images: List[ChannelImage]
            set of images that are all of the same *cycle* and *channel*
        dx: int, optional
            displacement in x direction in pixels; useful when images are
            acquired with an overlap in x direction (negative integer value)
        dy: int, optional
            displacement in y direction in pixels; useful when images are
            acquired with an overlap in y direction (negative integer value)
        stats: IllumstatsImages, optional
            illumination statistics to correct images for
            illumination artifacts

        Returns
        -------
        Mosaic

        Raises
        ------
        MetadataError
            when `images` are not of same *cycle* or *channel*
        '''
        cycles = [im.cycle for im in images]
        if len(cycles) > 1:
            raise MetadataError('All images must be of the same cycle')
        channels = [im.channel for im in images]
        if len(channels) > 1:
            raise MetadataError('All images must be of the same channel')
        grid = Mosaic._build_image_grid(images)
        rows = list()
        for i in xrange(grid.shape[0]):
            current_row = list()
            for j in xrange(grid.shape[1]):
                img = grid[i, j]
                if stats:
                    img = img.correct(stats.mean, stats.std)
                current_row.append(img.pixels.array)
            rows.append(reduce(lambda x, y: x.merge(y, 'horizontal', dx, 0),
                               current_row))
        img = reduce(lambda x, y: x.merge(y, 'vertical', 0, dy), rows)
        return Mosaic(img)
