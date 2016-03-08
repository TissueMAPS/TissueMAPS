import logging
from abc import ABCMeta

logger = logging.getLogger(__name__)


class ImageMetadata(object):

    '''
    Base class for image metadata, such as the name of the channel or
    the relative position of the image within the well (acquisition grid).
    '''

    __metaclass__ = ABCMeta

    _PERSISTENT_ATTRS = {
        'id', 'name', 'zplane', 'tpoint', 'site',
        'plate', 'well_name', 'well_position_x', 'well_position_y',
        'x_shift', 'y_shift',
        'upper_overhang', 'lower_overhang', 'right_overhang', 'left_overhang',
        'is_aligned', 'is_omitted'
    }

    def __init__(self):
        '''
        Initialize an instance of class ImageMetadata.

        Returns
        -------
        tmlib.metadata.ImageMetadata

        Note
        ----
        Values of shift and overhang attributes are set to zero.

        See also
        --------
        :mod:`tmlib.align.description.AlignmentDescription`
        '''
        self.is_aligned = False
        self.is_omitted = False
        self.upper_overhang = 0
        self.lower_overhang = 0
        self.right_overhang = 0
        self.left_overhang = 0
        self.x_shift = 0
        self.y_shift = 0

    @property
    def id(self):
        '''
        Returns
        -------
        int
            zero-based unique image identifier number
        '''
        return self._id

    @id.setter
    def id(self, value):
        if not(isinstance(value, int)):
            raise TypeError('Attribute "id" must have type int')
        self._id = value

    @property
    def name(self):
        '''
        Returns
        -------
        str
            name of the image (the same as the name of the corresponding file
            on disk)
        '''
        return self._name

    @name.setter
    def name(self, value):
        if not(isinstance(value, basestring)):
            raise TypeError('Attribute "name" must have type str')
        self._name = str(value)

    @property
    def plate(self):
        '''
        Returns
        -------
        int
            zero-based index of the plate to which the image belongs
        '''
        return self._plate

    @plate.setter
    def plate(self, value):
        if not(isinstance(value, int)):
            raise TypeError('Attribute "plate" must have type int')
        self._plate = value

    @property
    def site(self):
        '''
        Returns
        -------
        int
            zero-based global (plate-wide) acquisition-site index

        Note
        ----
        The index doesn't follow any particular order, it just indicates which
        images where acquired at the same "site", i.e. microscope stage
        position.
        '''
        return self._site

    @site.setter
    def site(self, value):
        if not(isinstance(value, int)):
            raise TypeError('Attribute "site" must have type int')
        self._site = value

    @property
    def well_position_y(self):
        '''
        Returns
        -------
        int
            zero-based row (y) index of the image within the well
        '''
        return self._well_position_y

    @well_position_y.setter
    def well_position_y(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "well_position_y" must have type int')
        self._well_position_y = int(value)

    @property
    def well_position_x(self):
        '''
        Returns
        -------
        int
            zero-based column (x) index of the image within the well
        '''
        return self._well_position_x

    @well_position_x.setter
    def well_position_x(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "well_position_x" must have type int')
        self._well_position_x = int(value)

    @property
    def well_name(self):
        '''
        Returns
        -------
        str
            well identifier string, e.g. "A01"
        '''
        return self._well_name

    @well_name.setter
    def well_name(self, value):
        if not(isinstance(value, basestring)):
            raise TypeError('Attribute "well_name" must have type str')
        self._well_name = str(value)

    @property
    def zplane(self):
        '''
        Returns
        -------
        int
            zero-based z index of the focal plane within a three dimensional
            stack
        '''
        return self._zplane

    @zplane.setter
    def zplane(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "zplane" must have type int')
        self._zplane = value

    @property
    def tpoint(self):
        '''
        Returns
        -------
        int
            zero-based index of the time point in the time series
        '''
        return self._tpoint

    @tpoint.setter
    def tpoint(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "tpoint" must have type int')
        self._tpoint = value

    @property
    def cycle_ix(self):
        '''
        Returns
        -------
        int
            zero-based index of the corresponding cycle
        '''
        return self._cycle_ix

    @cycle_ix.setter
    def cycle_ix(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "cycle_ix" must have type int')
        self._cycle_ix = value

    @property
    def upper_overhang(self):
        '''
        Returns
        -------
        int
            overhang in pixels at the upper side of the image
            relative to the corresponding image in the reference cycle
        '''
        return self._upper_overhang

    @upper_overhang.setter
    def upper_overhang(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "upper_overhang" must have type int')
        self._upper_overhang = value

    @property
    def lower_overhang(self):
        '''
        Returns
        -------
        int
            overhang in pixels at the lower side of the image
            relative to the corresponding image in the reference cycle
        '''
        return self._lower_overhang

    @lower_overhang.setter
    def lower_overhang(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "lower_overhang" must have type int')
        self._lower_overhang = value

    @property
    def left_overhang(self):
        '''
        Returns
        -------
        int
            overhang in pixels at the left side of the image
            relative to the corresponding image in the reference cycle
        '''
        return self._left_overhang

    @left_overhang.setter
    def left_overhang(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "left_overhang" must have type int')
        self._left_overhang = value

    @property
    def right_overhang(self):
        '''
        Returns
        -------
        int
            overhang in pixels at the right side of the image
            relative to the corresponding image in the reference cycle
        '''
        return self._right_overhang

    @right_overhang.setter
    def right_overhang(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "right_overhang" must have type int')
        self._right_overhang = value

    @property
    def x_shift(self):
        '''
        Returns
        -------
        int
            shift of the image in pixels in x direction relative to the
            corresponding image in the reference cycle
        '''
        return self._x_shift

    @x_shift.setter
    def x_shift(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "x_shift" must have type int')
        self._x_shift = value

    @property
    def y_shift(self):
        '''
        Returns
        -------
        int
            shift of the image in pixels in y direction relative to the
            corresponding image in the reference cycle
        '''
        return self._y_shift

    @y_shift.setter
    def y_shift(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "y_shift" must have type int')
        self._y_shift = value

    @property
    def is_omitted(self):
        '''
        Returns
        -------
        bool
            whether the image should be omitted from further analysis
            (for example because the shift exceeds the maximally tolerated
             shift or because the image contains artifacts)
        '''
        return self._is_omitted

    @is_omitted.setter
    def is_omitted(self, value):
        if not isinstance(value, bool):
            raise TypeError('Attribute "omit" must have type bool')
        self._is_omitted = value

    @property
    def is_aligned(self):
        '''
        Returns
        -------
        bool
            indicates whether the image has been aligned
        '''
        return self._is_aligned

    @is_aligned.setter
    def is_aligned(self, value):
        if not isinstance(value, bool):
            raise TypeError('Attribute "is_aligned" must have type bool')
        self._is_aligned = value


class ChannelImageMetadata(ImageMetadata):

    '''
    Class for metadata specific to channel images, e.g. images acquired with
    a fluorescence microscope.
    '''

    _PERSISTENT_ATTRS = ImageMetadata._PERSISTENT_ATTRS.union({
        'channel_name', 'is_corrected', 'channel'
    })

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class ChannelImageMetadata.

        Parameters
        ----------
        **kwargs: dict, optional
            metadata attributes as key-value pairs

        Returns
        -------
        :py:class:`tmlib.metadata.ChannelImageMetadata`
        '''
        super(ChannelImageMetadata, self).__init__()
        self.is_corrected = False
        if kwargs:
            for a in self._PERSISTENT_ATTRS:
                if a not in kwargs and not hasattr(self, a):
                    raise ValueError('Argument "kwargs" requires key "%s"' % a)
            for key, value in kwargs.iteritems():
                if key in self._PERSISTENT_ATTRS:
                    setattr(self, key, value)
                else:
                    logger.warning('attribute "%s" is not set', key)

    @property
    def channel_name(self):
        '''
        Returns
        -------
        str
            name given to the channel
        '''
        return self._channel_name

    @channel_name.setter
    def channel_name(self, value):
        if not isinstance(value, basestring):
            raise TypeError('Attribute "channel_name" must have type str')
        self._channel_name = str(value)

    @property
    def channel(self):
        '''
        Returns
        -------
        int
            zero-based channel identifier number
        '''
        return self._channel

    @channel.setter
    def channel(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "channel" must have type int')
        self._channel = value

    @property
    def is_corrected(self):
        '''
        Returns
        -------
        bool
            in case the image is illumination corrected
        '''
        return self._is_corrected

    @is_corrected.setter
    def is_corrected(self, value):
        if not isinstance(value, bool):
            raise TypeError('Attribute "is_corrected" must have type bool')
        self._is_corrected = value

    def __iter__(self):
        for attr in dir(self):
            if attr in self._PERSISTENT_ATTRS:
                if hasattr(self, attr):
                    yield (attr, getattr(self, attr))
                else:
                    raise AttributeError(
                            '"%s" object doesn\'t have attribute "%s"'
                            % (self.__class__.__name__, attr))

    def __str__(self):
        # TODO: pretty print
        pass


class ImageFileMapping(object):

    '''
    Container for information about the location of individual images (planes)
    within the original image file and references to the files in which they
    will be stored upon extraction.
    '''

    _PERSISTENT_ATTRS = {
        'files', 'series', 'planes', 'ref_index', 'ref_file'
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
                if key in self._PERSISTENT_ATTRS:
                    setattr(self, key, value)

    @property
    def files(self):
        '''
        Returns
        -------
        str
            absolute path to the required original image files
        '''
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
        '''
        Returns
        -------
        int
            zero-based position index of the required series in the original
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
        '''
        Returns
        -------
        int
            zero-based position index of the required planes in the original
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
        '''
        Returns
        -------
        List[str]
            index of the image in the image *Series* in the OMEXML
        '''
        return self._ref_index

    @ref_index.setter
    def ref_index(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "ref_index" must have type int')
        self._ref_index = value

    @property
    def ref_file(self):
        '''
        Returns
        -------
        List[str]
            absolute path to the final image file
        '''
        return self._ref_file

    @ref_file.setter
    def ref_file(self, value):
        if not isinstance(value, basestring):
            raise TypeError('Attribute "ref_file" must have type str')
        self._ref_file = value

    def __iter__(self):
        '''
        Returns
        -------
        dict
            key-value representation of the object
            (only `_PERSISTENT_ATTRS` attributes)

        Examples
        --------
        >>>obj = ImageFileMapping()
        >>>obj.series = [0, 0]
        >>>obj.planes = [0, 1]
        >>>obj.files = ["a", "b"]
        >>>obj.ref_index = 0
        >>>obj.ref_file = "c"
        >>>obj.ref_id = "Image:0"
        >>>dict(obj)
        {'series': [0, 0], 'planes': [0, 1], 'ref_id': 'Image:0', 'ref_index': 0, 'filenames': ['a', 'b'], 'ref_name': 'c'}
        '''
        for attr in dir(self):
            if attr not in self._PERSISTENT_ATTRS:
                continue
            yield (attr, getattr(self, attr))


class IllumstatsImageMetadata(object):

    '''
    Class for metadata specific to illumination statistics images.
    '''

    def __init__(self):
        self.is_smoothed = False

    @property
    def tpoint(self):
        '''
        Returns
        -------
        int
            one-based time point identifier number
        '''
        return self._tpoint

    @tpoint.setter
    def tpoint(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "tpoint" must have type int')
        self._tpoint = value

    @property
    def channel(self):
        '''
        Returns
        -------
        int
            zero-based channel index
        '''
        return self._channel

    @channel.setter
    def channel(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "channel" must have type int.')
        self._channel = value

    @property
    def is_smoothed(self):
        return self._is_smoothed
    
    @is_smoothed.setter
    def is_smoothed(self, value):
        if not isinstance(value, bool):
            raise TypeError('Attribute "is_smoothed" must have type bool.')
        self._is_smoothed = value

    @property
    def filename(self):
        '''
        Returns
        -------
        str
            name of the statistics file
        '''
        return self._filename

    @filename.setter
    def filename(self, value):
        if not isinstance(value, basestring):
            raise TypeError('Attribute "filename" must have type basestring')
        self._filename = str(value)


class ChannelLayerMetadata(object):

    '''
    Class for metadata of :py:class:`tmlib.layer.ChannelLayer`.
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
        if not(isinstance(value, basestring)):
            raise TypeError('Attribute "name" must have type basestring')
        self._name = str(value)

    @property
    def zplane(self):
        '''
        Returns
        -------
        int
            zero-based z index of the focal plane within a three dimensional
            stack
        '''
        return self._zplane

    @zplane.setter
    def zplane(self, value):
        if not(isinstance(value, int)):
            raise TypeError('Attribute "zplane" must have type int')
        self._zplane = value

    @property
    def tpoint(self):
        '''
        Returns
        -------
        int
            one-based time point identifier number
        '''
        return self._tpoint

    @tpoint.setter
    def tpoint(self, value):
        if not(isinstance(value, int)):
            raise TypeError('Attribute "tpoint" must have type int')
        self._tpoint = value

    @property
    def channel(self):
        '''
        Returns
        -------
        int
            channel index
        '''
        return self._channel

    @channel.setter
    def channel(self, value):
        if not(isinstance(value, int)):
            raise TypeError('Attribute "channel" must have type int')
        self._channel = value

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
        if not(isinstance(value, list)):
            raise TypeError('Attribute "sites" must have type list')
        if not(all([isinstance(v, int) for v in value])):
            raise TypeError('Elements of "sites" must have type int')
        self._sites = value

    @property
    def filenames(self):
        '''
        Returns
        -------
        List[str]
            absolute paths to the image files the mosaic is composed of
        '''
        return self._filenames

    @filenames.setter
    def filenames(self, value):
        if not(isinstance(value, list)):
            raise TypeError('Attribute "filenames" must have type list')
        if not(all([isinstance(v, basestring) for v in value])):
            raise TypeError('Elements of "filenames" must have type str')
        self._filenames = [str(v) for v in value]
