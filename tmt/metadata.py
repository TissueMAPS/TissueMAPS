from abc import ABCMeta
from abc import abstractmethod


class Metadata(object):

    '''
    Abstract base class for the metadata of an image, such as its
    relative position within the acquisition grid.
    '''

    __metaclass__ = ABCMeta

    required_metadata = {
        'orig_filename', 'name', 'cycle', 'dtype', 'dimensions',
        'position', 'well'
    }

    persistent_metadata = {
        'filename', 'name', 'cycle', 'dtype', 'dimensions',
        'site', 'row', 'column', 'well'
    }

    def __init__(self, metadata=None):
        '''
        Initialize an instance of class Metadata.

        Parameters
        ----------
        metadata: Dict[str, int or str or tuple]
            metadata read from a *.metadata* JSON file
        '''
        self.metadata = metadata
        if self.metadata:
            self.set(self.metadata)

    @property
    def cycle(self):
        '''
        Returns
        -------
        int
            one-based cycle identifier number
        '''
        return self._cycle

    @cycle.setter
    def cycle(self, value):
        self._cycle = value

    @property
    def filename(self):
        '''
        Returns
        -------
        str
            name of the corresponding image file
        '''
        return self._filename

    @filename.setter
    def filename(self, value):
        self._filename = value

    @property
    def orig_filename(self):
        '''
        Returns
        -------
        str
            name of the original image file
        '''
        return self._orig_filename

    @orig_filename.setter
    def orig_filename(self, value):
        self._orig_filename = value

    @property
    def series(self):
        '''
        Returns
        -------
        int
            identifier number of the series within the original image file
        '''
        return self._series

    @series.setter
    def series(self, value):
        self._series = value

    @property
    def name(self):
        '''
        Returns
        -------
        str
            name of the image (given by the microscope)
        '''
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def dtype(self):
        '''
        Returns
        -------
        int
            data type of the image pixel array
        '''
        return self._dtype

    @dtype.setter
    def dtype(self, value):
        self._dtype = value

    @property
    def dimensions(self):
        '''
        Returns
        -------
        int
            dimensions of the image pixel array
        '''
        return self._dimensions

    @dimensions.setter
    def dimensions(self, value):
        self._dimensions = value

    @property
    def site(self):
        '''
        Returns
        -------
        int
            one-based unique position index

        Note
        ----
        Sites are not necessarily sorted according to acquisition time.
        '''
        return self._site

    @site.setter
    def site(self, value):
        self._site = value

    @property
    def position(self):
        '''
        Returns
        -------
        Tuple[float]
            absolute y, x microscope stage positions
        '''
        return self._position

    @position.setter
    def position(self, value):
        self._position = value

    @property
    def row(self):
        '''
        Returns
        -------
        int
            one-based row index of the image in the acquisition grid
        '''
        return self._row

    @row.setter
    def row(self, value):
        self._row = value

    @property
    def column(self):
        '''
        Returns
        -------
        int
            one-based column index of the image in the acquisition grid
        '''
        return self._column

    @column.setter
    def column(self, value):
        self._row = value

    @property
    def grid_coordinates(self):
        '''
        Returns
        -------
        Tuple[int]
            zero-based row, column indices of the image in the acquisition grid
        '''
        self._coordinates = (self.row-1, self.column-1)
        return self._coordinates

    @property
    def well(self):
        '''
        Returns
        -------
        Tuple[int] or None
            one-based row, column indices of the well in the plate
        '''
        return self._well

    @well.setter
    def well(self, value):
        self._well = value

    @property
    def plate_coordinates(self):
        '''
        Returns
        -------
        Tuple[int]
            zero-based row, column indices of the well in the plate
        '''
        self._well_coordinates = (self.well[0]-1, self.well[1]-1)
        return self._well_coordinates

    @abstractmethod
    def serialize(self):
        '''
        Serialize required metadata attributes to key-value pairs.
        '''
        pass

    @abstractmethod
    def set(self, metadata):
        '''
        Set attributes from key-value pairs in dictionary.
        '''
        pass


class ChannelMetadata(Metadata):

    '''
    Class for metadata specific to channel images.
    '''

    required_metadata = Metadata.required_metadata.union({
                            'channel', 'channel_name'
    })

    def __init__(self, metadata=None):
        '''
        Initialize an instance of class ChannelMetadata.

        Parameters
        ----------
        metadata: Dict[str, int or str]
            image metadata read from the *.metadata* JSON file
        '''
        super(ChannelMetadata, self).__init__(metadata)
        self.metadata = metadata
        if self.metadata:
            self.set(self.metadata)

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
        self._channel_name = value

    @property
    def channel(self):
        '''
        Returns
        -------
        int
            one-based channel identifier number
        '''
        return self._channel

    @channel.setter
    def channel(self, value):
        self._channel = value

    @property
    def channel_planes(self):
        '''
        Returns
        -------
        List[]
        '''
        return self._channel_planes

    @channel_planes.setter
    def channel_planes(self, value):
        self._channel_planes = value

    def serialize(self):
        '''
        Serialize persistent metadata attributes to key-value pairs.

        Returns
        -------
        Dict[str, str or int or tuple]
            metadata as key-value pairs
        
        Raises
        ------
        AttributeError
            when instance doesn't have a required attribute
        '''
        serialized_metadata = dict()
        for a in dir(self):
            if a in ChannelMetadata.persistent_metadata:
                if not hasattr(self, a):
                    raise AttributeError('Object "%s" has no attribute "%s"'
                                         % (self.__name__, a))
                serialized_metadata[a] = getattr(self, a)
        return serialized_metadata

    def set(self, metadata):
        '''
        Set attributes based on values in dictionary.

        Parameters
        ----------
        metadata: Dict[str, str or int or tuple]
            metadata as key-value pairs

        Raises
        ------
        KeyError
            when keys for required attributes are not provided
        AttributeError
            when keys are provided that don't have a corresponding attribute
        '''
        missing_keys = [a for a in ChannelMetadata.persistent_metadata
                        if a not in metadata.keys()]
        if len(missing_keys) > 0:
            raise KeyError('Missing keys: "%s"' % '", "'.join(missing_keys))
        for k, v in metadata:
            if k not in ChannelMetadata.persistent_metadata:
                raise AttributeError('Object "%s" has no attribute "%s"'
                                     % (self.__name__, k))
            setattr(self, k, v)


class SegmentationMetadata(Metadata):

    '''
    Class for metadata specific to segmentation images.
    '''

    required_metadata = Metadata.required_metadata.union({'objects'})

    def __init__(self, metadata=None):
        '''
        Initialize an instance of class SegmentationMetadata.

        Parameters
        ----------
        metadata: Dict[str, int or str]
            image metadata read from the *.metadata* JSON file
        '''
        super(SegmentationMetadata, self).__init__(metadata)
        self.metadata = metadata
        if self.metadata:
            self._objects = self.metadata['objects']

    @property
    def objects(self):
        '''
        Returns
        -------
        str
            name given to the objects in the image

        '''
        return self._objects

    @objects.setter
    def objects(self, value):
        self._objects = value

    def serialize(self):
        '''
        Serialize required metadata attributes to key-value pairs.

        Returns
        -------
        Dict[str, str or int or tuple]
            required metadata as key-value pairs
        
        Raises
        ------
        AttributeError
            when instance doesn't have a required attribute
        '''
        serialized_metadata = dict()
        for a in dir(self):
            if a in SegmentationMetadata.required_metadata:
                if not hasattr(self, a):
                    raise AttributeError('Object "%s" has no attribute "%s"'
                                         % (self.__name__, a))
                serialized_metadata[a] = getattr(self, a)
        return serialized_metadata

    def set(self, metadata):
        '''
        Set attributes based on values in dictionary.

        Parameters
        ----------
        metadata: Dict[str, str or int or tuple]
            metadata as key-value pairs

        Raises
        ------
        KeyError
            when keys for required attributes are not provided
        AttributeError
            when keys are provided that don't have a corresponding attribute
        '''
        missing_keys = [a for a in SegmentationMetadata.required_metadata
                        if a not in metadata.keys()]
        if len(missing_keys) > 0:
            raise KeyError('Missing keys: "%s"' % '", "'.join(missing_keys))
        for k, v in metadata:
            if k not in SegmentationMetadata.required_metadata:
                raise AttributeError('Object "%s" has no attribute "%s"'
                                     % (self.__name__, k))
            setattr(self, k, v)
