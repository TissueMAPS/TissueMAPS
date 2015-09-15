from gi.repository import Vips


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


class MosaicMetadata(object):

    '''
    Class for mosaic image metadata, such as the name of the channel or
    the relative position of the mosaic within a well plate.
    '''

    @property
    def name(self):
        '''
        Returns
        -------
        str
            name of the corresponding layer
        '''
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

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
    def sites(self):
        '''
        Returns
        -------
        List[int]
            site identifier numbers of images contained in the mosaic
        '''
        return self._sites

    @sites.setter
    def sites(self, value):
        self._sites = value
