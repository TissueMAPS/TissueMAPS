import logging
from abc import ABCMeta

from tmlib.utils import assert_type

logger = logging.getLogger(__name__)


class ChannelImageMetadata(object):

    '''Class for metadata that describes channel images.'''

    def __init__(self, channel_id, site_id, cycle_id, tpoint, **kwargs):
        '''
        Parameters
        ----------
        channel_id: int
            channel ID
        site_id: int
            site ID
        cycle_id: int
            cycle ID
        tpoint: int
            zero-based time point index
        **kwargs: dict, optional
            additional keyword arguments
        '''
        self.tpoint = tpoint
        self.channel_id = channel_id
        self.cycle_id = cycle_id
        self.is_corrected = False
        self.is_rescaled = False
        self.is_clipped = False
        self.is_aligned = False
        self.is_omitted = False
        self.upper_overhang = 0
        self.lower_overhang = 0
        self.right_overhang = 0
        self.left_overhang = 0
        self.x_shift = 0
        self.y_shift = 0
        for key, value in kwargs.iteritems():
            if hasattr(self.__class__, key):
                if isinstance(getattr(self.__class__, key), property):
                    setattr(self, key, value)

    @property
    def upper_overhang(self):
        '''int: overhang in pixels at the upper side of the image
        relative to the site in the reference cycle
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
        relative to the site in the reference cycle
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
        relative to the site in the reference cycle
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
        relative to the site in the reference cycle
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
        site in the reference cycle
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
        site in the reference cycle
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

    def __repr__(self):
        return (
            '<%s(channel_id=%r, site_id=%r, cycle_id=%r, tpoint=%r)' % (
                self.__class__.__name__, self.channel_id,
                self.site_id, self.cycle_id, self.tpoint
            )
        )


class ImageFileMapping(object):

    '''Class for a mapping of an extracted image file to microscope image
    file(s) and the location of the individual pixel planes within these files.
    '''

    def __init__(self, **kwargs):
        '''
        Parameters
        ----------
        kwargs: dict, optional
            file mapping as key-value pairs
        '''
        for key, value in kwargs.iteritems():
            if hasattr(self.__class__, key):
                if isinstance(getattr(self.__class__, key), property):
                    setattr(self, key, value)

    @property
    def files(self):
        '''str: absolute path to the microscope image files'''
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
    def zlevels(self):
        '''int: zero-based position index of the required planes in the source
        file
        '''
        return self._zlevels

    @zlevels.setter
    def zlevels(self, value):
        if not isinstance(value, list):
            raise TypeError('Attribute "zlevels" must have type list')
        if not all([isinstance(v, int) for v in value]):
            raise TypeError('Elements of "zlevels" must have type int')
        self._zlevels = value

    @property
    def ref_index(self):
        '''int: index of the image in the OMEXML *Series*'''
        return self._ref_index

    @ref_index.setter
    def ref_index(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "ref_index" must have type int.')
        self._ref_index = value

    def to_dict(self):
        '''
        Returns
        -------
        dict
            mapping as key-values

        Examples
        --------
        >>>ifm = ImageFileMapping()
        >>>ifm.series = [0, 0]
        >>>ifm.planes = [0, 1]
        >>>ifm.files = ["a", "b"]
        >>>ifm.zlevels = [0, 1]
        >>>ifm.to_dict()
        {'series': [0, 0], 'planes': [0, 1], 'files': ['a', 'b'], 'zlevels': [0, 1]}

        >>>ifm = ImageFileMapping(
        ...    series=[0, 0],
        ...    planes=[0, 1],
        ...    files=["a", "b"],
        ...    zlevels=[0, 1]
        ...)
        >>>ifm.to_dict()
        {'series': [0, 0], 'planes': [0, 1], 'files': ['a', 'b'], 'zlevels': [0, 1]}
        '''
        mapping = dict()
        for attr in dir(self):
            if hasattr(self.__class__, attr):
                if isinstance(getattr(self.__class__, attr), property):
                    mapping[attr] = getattr(self, attr)
        return mapping

    def __repr__(self):
        return '%s(ref_index=%r)' % (self.__class__.__name__, self.ref_index)


class SegmentationImageMetadata(object):

    '''Class for metadata to describe a segmentation image.'''

    def __init__(self, mapobject_type_id, site_id):
        '''
        Parameters
        ----------
        mapobject_type_id: int
            mapobject type ID
        site_id: int
            site ID
        '''
        self.mapobject_type_id = mapobject_type_id
        self.site_id = site_id

    def __repr__(self):
        return '%s(mapobject_type_id=%r, site_id=%r)' % (
            self.__class__.__name__, self.mapobject_type_id, self.site_id
        )


class PyramidTileMetadata(object):

    '''Class for metadata to describe a pyramid tile.'''

    def __init__(self, level, row, column, channel_layer_id):
        '''
        Parameters
        ----------
        level: int
            zero-based zoom level index
        row: int
            zero-based row index
        column: int
            zero-based column index
        channel_layer_id: int
            channel layer ID
        '''
        self.level = level
        self.row = row
        self.column = column
        self.channel_layer_id = channel_layer_id

    def __repr__(self):
        return '%s(level=%r, row=%r, column=%r, channel_layer_id=%r)' % (
            self.__class__.__name__, self.level, self.row, self.column,
            self.channel_layer_id
        )


class IllumstatsImageMetadata(object):

    '''Class for metadata to describe an illumination statistics image.'''

    @assert_type(cycle_id='int', channel_id='int')
    def __init__(self, cycle_id, channel_id):
        '''
        Parameters
        ----------
        cycle_id: int
            cycle ID
        channel_id: int
            channel ID
        '''
        self.cycle_id = cycle_id
        self.channel_id = channel_id
        self.is_smoothed = False

    @property
    def is_smoothed(self):
        '''bool: whether the illumination statistics image has been smoothed'''
        return self._is_smoothed

    @is_smoothed.setter
    def is_smoothed(self, value):
        if not isinstance(value, bool):
            raise TypeError('Attribute "is_smoothed" must have type bool.')
        self._is_smoothed = value

    def __repr__(self):
        return '%s(cycle_id=%r, channel_id=%r)' % (
            self.__class__.__name__, self.cycle_id, self.channel_id
        )
