import logging
from abc import ABCMeta

from tmlib.utils import assert_type

logger = logging.getLogger(__name__)


class ChannelImageMetadata(object):

    '''Base class for image metadata, such as the name of the channel or
    the relative position of the image within the well (acquisition grid).
    '''

    __metaclass__ = ABCMeta

    _SUPPORTED_KWARGS = {
        'x_shift', 'y_shift',
        'upper_overhang', 'lower_overhang', 'right_overhang', 'left_overhang',
        'is_aligned', 'is_omitted', 'is_corrected'
    }

    # @assert_type()
    def __init__(self, name, zplane, tpoint, plate, well, x, y, channel,
                 wavelength, cycle, **kwargs):
        '''
        Parameters
        ----------
        name: str
            name of the image (the same as that of the corresponding file)
        plate: str
            name of the corresponding plate
        well: str
            name of the corresponding well
        y: int
            zero-based row index of the image within the corresponding well
        x: int
            zero-based column index of the image within the corresponding well
        cycle: int
            zero-based index of the corresponding cycle based on the order
            of acquisition
        channel: int
            zero-based index of the corresponding channel
        wavelength: str
            name of the corresponding wavelength
        **kwargs: dict, optional
            metadata attributes as keyword arguments
        '''
        self.name = name
        self.zplane = zplane
        self.tpoint = tpoint
        self.plate = plate
        self.well = well
        self.y = y
        self.x = x
        self.channel = channel
        self.wavelength = wavelength
        self.cycle = cycle
        self.is_corrected = False
        self.is_aligned = False
        self.is_omitted = False
        self.upper_overhang = 0
        self.lower_overhang = 0
        self.right_overhang = 0
        self.left_overhang = 0
        self.x_shift = 0
        self.y_shift = 0
        if kwargs:
            for key, value in kwargs.iteritems():
                if key in self._SUPPORTED_KWARGS:
                    setattr(self, key, value)
                else:
                    logger.warning('argument "%s" is ignored', key)

    @property
    def upper_overhang(self):
        '''int: overhang in pixels at the upper side of the image
        relative to the corresponding site in the reference cycle
        '''
        return self._upper_overhang

    @upper_overhang.setter
    def upper_overhang(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "upper_overhang" must have type int')
        self._upper_overhang = value

    @property
    def lower_overhang(self):
        '''int: overhang in pixels at the lower side of the image
        relative to the corresponding site in the reference cycle
        '''
        return self._lower_overhang

    @lower_overhang.setter
    def lower_overhang(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "lower_overhang" must have type int')
        self._lower_overhang = value

    @property
    def left_overhang(self):
        '''int: overhang in pixels at the left side of the image
        relative to the corresponding site in the reference cycle
        '''
        return self._left_overhang

    @left_overhang.setter
    def left_overhang(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "left_overhang" must have type int')
        self._left_overhang = value

    @property
    def right_overhang(self):
        '''int: overhang in pixels at the right side of the image
        relative to the corresponding site in the reference cycle
        '''
        return self._right_overhang

    @right_overhang.setter
    def right_overhang(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "right_overhang" must have type int')
        self._right_overhang = value

    @property
    def x_shift(self):
        '''int: shift of the image in pixels in x direction relative to the
        corresponding site in the reference cycle
        '''
        return self._x_shift

    @x_shift.setter
    def x_shift(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "x_shift" must have type int')
        self._x_shift = value

    @property
    def y_shift(self):
        '''int: shift of the image in pixels in y direction relative to the
        corresponding site in the reference cycle
        '''
        return self._y_shift

    @y_shift.setter
    def y_shift(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "y_shift" must have type int.')
        self._y_shift = value

    @property
    def is_corrected(self):
        '''bool: whether the image is corrected for illumination artifacts'''
        return self._is_corrected

    @is_corrected.setter
    def is_corrected(self, value):
        if not isinstance(value, bool):
            raise TypeError('Attribute "is_corrected" must have type bool')
        self._is_corrected = value

    @property
    def is_omitted(self):
        '''bool: whether the image should be omitted from further analysis'''
        return self._is_omitted

    @is_omitted.setter
    def is_omitted(self, value):
        if not isinstance(value, bool):
            raise TypeError('Attribute "omit" must have type bool.')
        self._is_omitted = value

    @property
    def is_aligned(self):
        '''bool: whether the image has been aligned between cycles'''
        return self._is_aligned

    @is_aligned.setter
    def is_aligned(self, value):
        if not isinstance(value, bool):
            raise TypeError('Attribute "is_aligned" must have type bool.')
        self._is_aligned = value


class ImageFileMapping(object):

    '''Container for information about the location of individual images
    (planes) within the microscope image file and references to the files in
    which they will be stored upon extraction.
    '''

    _SUPPORTED_ATTRS = {
        'files', 'series', 'planes'
    }

    def __init__(self, **kwargs):
        '''
        Parameters
        ----------
        kwargs: dict, optional
            file mapping key-value pairs
        '''
        if kwargs:
            for key, value in kwargs.iteritems():
                setattr(self, key, value)

    @property
    def files(self):
        '''str: absolute path to the required original image files'''
        return self._files

    @files.setter
    def files(self, value):
        if not isinstance(value, list):
            raise TypeError('Attribute "files" must have type list')
        if not all([isinstance(v, basestring) for v in value]):
            raise TypeError('Elements of "files" must have type str')
        self._files = value

    @property
    def series(self):
        '''int:zero-based position index of the required series in the source
        file
        '''
        return self._series

    @series.setter
    def series(self, value):
        if not isinstance(value, list):
            raise TypeError('Attribute "series" must have type list')
        if not all([isinstance(v, int) for v in value]):
            raise TypeError('Elements of "series" must have type int')
        self._series = value

    @property
    def planes(self):
        '''int: zero-based position index of the required planes in the source
        file
        '''
        return self._planes

    @planes.setter
    def planes(self, value):
        if not isinstance(value, list):
            raise TypeError('Attribute "planes" must have type list')
        if not all([isinstance(v, int) for v in value]):
            raise TypeError('Elements of "planes" must have type int')
        self._planes = value

    @property
    def ref_index(self):
        '''int: index of the image in the OMEXML *Series*'''
        return self._ref_index

    @ref_index.setter
    def ref_index(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "ref_index" must have type int.')
        self._ref_index = value

    def __iter__(self):
        '''
        Returns
        -------
        dict
            key-value representation of the object
            (only `_SUPPORTED_ATTRS` attributes)

        Examples
        --------
        >>>obj = ImageFileMapping()
        >>>obj.series = [0, 0]
        >>>obj.planes = [0, 1]
        >>>obj.files = ["a", "b"]
        >>>dict(obj)
        {'series': [0, 0], 'planes': [0, 1], 'files': ['a', 'b']}
        '''
        for attr in dir(self):
            if attr not in self._SUPPORTED_ATTRS:
                continue
            yield (attr, getattr(self, attr))


class PyramidTileMetadata(object):

    def __init__(self, **kwargs):
        pass


class IllumstatsImageMetadata(object):

    '''
    Class for metadata specific to illumination statistics images.
    '''

    @assert_type(cycle='int', channel='int')
    def __init__(self, cycle, channel):
        '''
        Parameters
        ----------
        cycle: int
            zero-based index of the corresponding cycle based on the order
            of acquisition
        channel: int
            zero-based index of the corresponding channel
        '''
        self.cycle = cycle
        self.channel = channel
        self.is_smoothed = False

    @property
    def is_smoothed(self):
        return self._is_smoothed

    @is_smoothed.setter
    def is_smoothed(self, value):
        if not isinstance(value, bool):
            raise TypeError('Attribute "is_smoothed" must have type bool.')
        self._is_smoothed = value
