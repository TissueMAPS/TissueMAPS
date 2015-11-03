

class ImageMetadata(object):

    '''
    Base class for image metadata, such as the name of the channel or
    the relative position of the image within the acquisition grid.
    '''

    _PERSISTENT_ATTRS = {'id', 'name', 'zplane_ix', 'tpoint_ix', 'site_ix'}

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
        :mod:`tmlib.align.descriptions.AlignmentDescription`
        '''
        self.is_aligned = False
        self.is_corrected = False
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
    def plate_name(self):
        '''
        Returns
        -------
        str
            name of the plate to which the image belongs
        '''
        return self._plate_name

    @plate_name.setter
    def plate_name(self, value):
        if not(isinstance(value, basestring)):
            raise TypeError('Attribute "name" must have type str')
        self._plate_name = str(value)

    @property
    def site_ix(self):
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
        return self._site_ix

    @site_ix.setter
    def site_ix(self, value):
        if not(isinstance(value, int)):
            raise TypeError('Attribute "site_ix" must have type int')
        self._site_ix = value

    @property
    def well_pos_y(self):
        '''
        Returns
        -------
        int
            zero-based row (y) index of the image within the well
        '''
        return self._well_pos_y

    @well_pos_y.setter
    def well_pos_y(self, value):
        if not(isinstance(value, (int, float))):
            raise TypeError('Attribute "well_pos_y" must have type int or float')
        self._well_pos_y = int(value)

    @property
    def well_pos_x(self):
        '''
        Returns
        -------
        int
            zero-based column (x) index of the image within the well
        '''
        return self._well_pos_x

    @well_pos_x.setter
    def well_pos_x(self, value):
        if not(isinstance(value, (int, float))):
            raise TypeError('Attribute "well_pos_x" must have type int or float')
        self._well_pos_x = int(value)

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
        self._well_name = value

    @property
    def zplane_ix(self):
        '''
        Returns
        -------
        int
            zero-based z index of the focal plane within a three dimensional
            stack
        '''
        return self._zplane_ix

    @zplane_ix.setter
    def zplane_ix(self, value):
        if not(isinstance(value, int)) and value is not None:
            raise TypeError('Attribute "zplane_ix" must have type int')
        self._zplane_ix = value

    @property
    def tpoint_ix(self):
        '''
        Returns
        -------
        int
            one-based time point identifier number
        '''
        return self._tpoint_ix

    @tpoint_ix.setter
    def tpoint_ix(self, value):
        if not(isinstance(value, int)) and value is not None:
            raise TypeError('Attribute "tpoint_ix" must have type int')
        self._tpoint_ix = value

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
        if not(isinstance(value, int)) and value is not None:
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
        if not(isinstance(value, int)) and value is not None:
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
        if not(isinstance(value, int)) and value is not None:
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
        if not(isinstance(value, int)) and value is not None:
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
        if not(isinstance(value, int)) and value is not None:
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
        if not(isinstance(value, int)) and value is not None:
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
        'channel_name', 'is_corrected', 'channel_ix'
    })

    def __init__(self, metadata=None):
        '''
        Initialize an instance of class ChannelImageMetadata.

        Parameters
        ----------
        metadata: dict, optional
            metadata attributes as key-value pairs (default: ``None``)

        Returns
        -------
        tmlib.metadata.ChannelImageMetadata
        '''
        super(ChannelImageMetadata, self).__init__()
        self.is_corrected = False
        self.is_projected = False
        if metadata is not None:
            for key, value in metadata.iteritems():
                if key in self._PERSISTENT_ATTRS:
                    setattr(self, key, value)

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
        if not(isinstance(value, basestring)) and value is not None:
            raise TypeError('Attribute "channel_name" must have type str')
        self._channel_name = value

    @property
    def channel_ix(self):
        '''
        Returns
        -------
        int
            zero-based channel identifier number
        '''
        return self._channel_ix

    @channel_ix.setter
    def channel_ix(self, value):
        if not(isinstance(value, int)) and value is not None:
            raise TypeError('Attribute "channel_ix" must have type int')
        self._channel_ix = value

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
        '''
        Convert the object to a dictionary.

        Returns
        -------
        dict
            image metadata as key-value pairs

        Raises
        ------
        AttributeError
            when instance doesn't have a required attribute
        '''
        # TODO: site
        for attr in dir(self):
            if attr in self._PERSISTENT_ATTRS:
                yield (attr, getattr(self, attr))

    def __str__(self):
        # TODO: pretty print
        pass


class ImageFileMapper(object):

    '''
    Container for information about the location of individual images (planes)
    within the original image file and references to the files in which they
    will be stored upon extraction.
    '''

    _PERSISTENT_ATTRS = {
        'files', 'series', 'planes',
        'ref_index', 'ref_file', 'ref_id'
    }

    def __init__(self, **kwargs):
        '''
        Parameters
        ----------
        kwargs: dict, optional
            file mapping key-value pairs

        Returns
        -------
        tmlib.metadata.ImageFileMapper
            object where `_PERSISTENT_ATTRS` attributes where set with provided values
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
    def ref_id(self):
        '''
        Returns
        -------
        List[str]
            identifier string of the image in the configured OMEXML
            (pattern: (Image:\S+)); e.g. "Image:0")
        '''
        return self._ref_id

    @ref_id.setter
    def ref_id(self, value):
        if not isinstance(value, basestring):
            raise TypeError('Attribute "ref_id" must have type str')
        self._ref_id = value

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
        >>>obj = ImageFileMapper()
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

    @property
    def tpoint_ix(self):
        '''
        Returns
        -------
        int
            one-based time point identifier number
        '''
        return self._tpoint_ix

    @tpoint_ix.setter
    def tpoint_ix(self, value):
        if not(isinstance(value, int)) and value is not None:
            raise TypeError('Attribute "tpoint_ix" must have type int')
        self._tpoint_ix = value

    @property
    def channel_ix(self):
        '''
        Returns
        -------
        int
            zero-based channel index
        '''
        return self._channel_ix

    @channel_ix.setter
    def channel_ix(self, value):
        self._channel_ix = value

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
        self._filename = value


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
        if not(isinstance(value, basestring)):
            raise TypeError('Attribute "name" must have type str')
        self._name = str(value)

    @property
    def zplane_ix(self):
        '''
        Returns
        -------
        int
            zero-based z index of the focal plane within a three dimensional
            stack
        '''
        return self._zplane_ix

    @zplane_ix.setter
    def zplane_ix(self, value):
        if not(isinstance(value, int)):
            raise TypeError('Attribute "zplane_ix" must have type int')
        self._zplane_ix = value

    @property
    def tpoint_ix(self):
        '''
        Returns
        -------
        int
            one-based time point identifier number
        '''
        return self._tpoint_ix

    @tpoint_ix.setter
    def tpoint_ix(self, value):
        if not(isinstance(value, int)):
            raise TypeError('Attribute "tpoint_ix" must have type int')
        self._tpoint_ix = value

    @property
    def channel_ix(self):
        '''
        Returns
        -------
        int
            channel index
        '''
        return self._channel_ix

    @channel_ix.setter
    def channel_ix(self, value):
        if not(isinstance(value, int)):
            raise TypeError('Attribute "channel_ix" must have type int')
        self._channel_ix = value

    @property
    def site_ixs(self):
        '''
        Returns
        -------
        List[int]
            site identifier numbers of images contained in the mosaic
        '''
        return self._site_ixs

    @site_ixs.setter
    def site_ixs(self, value):
        if not(isinstance(value, list)):
            raise TypeError('Attribute "site_ixs" must have type list')
        if not(all([isinstance(v, int) for v in value])):
            raise TypeError('Elements of "site_ixs" must have type int')
        self._site_ixs = value

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
