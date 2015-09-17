from abc import ABCMeta
from abc import abstractmethod
from .errors import MetadataError


class ImageMetadata(object):

    '''
    Abstract base class for image metadata, such as the name of the channel or
    the relative position of the image within the acquisition grid.
    '''

    __metaclass__ = ABCMeta

    initially_required = {
        'original_filename', 'original_dtype', 'original_dimensions',
        'name', 'cycle', 'position', 'well'
    }

    persistent = {
        'original_filename', 'original_dtype', 'original_dimensions',
        'original_series', 'name', 'site', 'row', 'column', 'well'
    }

    def __init__(self, metadata=None):
        '''
        Initialize an instance of class ImageMetadata.

        Parameters
        ----------
        metadata: dict
            metadata for an individual image
        '''
        self.metadata = metadata
        if self.metadata:
            self.set(self.metadata)

    @property
    def original_filename(self):
        '''
        Returns
        -------
        str
            name of the original image file
        '''
        return self._original_filename

    @original_filename.setter
    def original_filename(self, value):
        self._original_filename = value

    @property
    def name(self):
        '''
        Returns
        -------
        str
            name of the image
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
    def cycle_id(self):
        '''
        Returns
        -------
        str
            identifier number of the corresponding cycle
        '''
        return self._cycle_id

    @cycle_id.setter
    def cycle_id(self, value):
        self._cycle_id = value

    @property
    def original_series(self):
        '''
        Returns
        -------
        int
            zero-based index of the image within the original image file
        '''
        return self._original_series

    @original_series.setter
    def original_series(self, value):
        self._original_series = value

    @property
    def original_dtype(self):
        '''
        Returns
        -------
        int
            data type of the image pixel array
        '''
        return self._original_dtype

    @original_dtype.setter
    def original_dtype(self, value):
        self._original_dtype = value

    @property
    def original_dimensions(self):
        '''
        Returns
        -------
        int
            y, x dimensions of the image in pixels
        '''
        return self._original_dimensions

    @original_dimensions.setter
    def original_dimensions(self, value):
        self._original_dimensions = value

    # TODO: Unfortunately, "PhysicalSize" attributes are not implemented
    # in python-bioformats

    # @property
    # def physical_dimensions(self):
    #     '''
    #     Returns
    #     -------
    #     int
    #         y, x dimensions of the image in micrometer
    #     '''
    #     return self._physical_dimensions

    # @physical_dimensions.setter
    # def physical_dimensions(self, value):
    #     self._physical_dimensions = value

    @property
    def site(self):
        '''
        Returns
        -------
        int
            one-based unique position identifier, sorted row-wise over all
            image acquisition sites

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
        self._column = value

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
        str
            well identifier string, e.g. "A01"
        '''
        return self._well

    @well.setter
    def well(self, value):
        self._well = value

    @abstractmethod
    def serialize(self):
        '''
        Serialize required metadata attributes to key-value pairs.
        '''
        pass

    @abstractmethod
    def set(metadata):
        '''
        Set attributes from key-value pairs in dictionary.
        '''
        pass


class ChannelImageMetadata(ImageMetadata):

    '''
    Class for metadata specific to channel images.
    '''

    persistent = ImageMetadata.persistent.union({'channel', 'original_planes'})

    def __init__(self, metadata=None):
        '''
        Initialize an instance of class ChannelImageMetadata.

        Parameters
        ----------
        metadata: Dict[str, int or str]
            image metadata read from the *.metadata* JSON file
        '''
        super(ChannelImageMetadata, self).__init__(metadata)
        self.metadata = metadata
        if self.metadata:
            self.set(self.metadata)

    @property
    def channel(self):
        '''
        Returns
        -------
        str
            name given to the channel
        '''
        return self._channel

    @channel.setter
    def channel(self, value):
        self._channel = value

    @property
    def original_planes(self):
        '''
        Returns
        -------
        List[int]
            zero-based index of channel planes within the image element
        '''
        return self._original_planes

    @original_planes.setter
    def original_planes(self, value):
        self._original_planes = value

    def serialize(self):
        '''
        Serialize attributes to key-value pairs.

        Returns
        -------
        dict
            metadata as key-value pairs

        Raises
        ------
        AttributeError
            when instance doesn't have a required attribute
        '''
        serialized_metadata = dict()
        for a in dir(self):
            if a in ChannelImageMetadata.persistent:
                serialized_metadata[a] = getattr(self, a)
        return serialized_metadata

    def set(self, metadata):
        '''
        Set attributes based on key-value pairs in dictionary.

        Parameters
        ----------
        metadata: dict
            metadata as key-value pairs

        Raises
        ------
        KeyError
            when keys for required attributes are not provided
        AttributeError
            when keys are provided that don't have a corresponding attribute
        '''
        missing_keys = [a for a in ChannelImageMetadata.persistent
                        if a not in metadata.keys()]
        if len(missing_keys) > 0:
            raise KeyError('Missing keys: "%s"' % '", "'.join(missing_keys))
        for k, v in metadata.iteritems():
            if k not in ChannelImageMetadata.persistent:
                raise AttributeError('Class "%s" has no attribute "%s"'
                                     % (ChannelImageMetadata.__class__.__name__, k))
            setattr(self, k, v)


class SegmentationImageMetadata(ImageMetadata):

    '''
    Class for metadata specific to segmentation images.
    '''

    persistent = ImageMetadata.persistent.union({'objects'})

    def __init__(self, metadata=None):
        '''
        Initialize an instance of class SegmentationImageMetadata.

        Parameters
        ----------
        metadata: Dict[str, int or str]
            image metadata read from the *.metadata* JSON file
        '''
        super(SegmentationImageMetadata, self).__init__(metadata)
        self.metadata = metadata
        if self.metadata:
            self.set(self.metadata)

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
            metadata as key-value pairs

        Raises
        ------
        AttributeError
            when instance doesn't have a required attribute
        '''
        serialized_metadata = dict()
        for a in dir(self):
            if a in SegmentationImageMetadata.persistent:
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
        missing_keys = [a for a in SegmentationImageMetadata.persistent
                        if a not in metadata.keys()]
        if len(missing_keys) > 0:
            raise KeyError('Missing keys: "%s"' % '", "'.join(missing_keys))
        for k, v in metadata:
            if k not in SegmentationImageMetadata.persistent:
                raise AttributeError('Object "%s" has no attribute "%s"'
                                     % (self.__name__, k))
            setattr(self, k, v)


class IllumstatsImageMetadata(object):

    '''
    Class for metadata specific to illumination statistics images.
    '''

    persistent = {'channel', 'cycle'}

    def __init__(self):
        '''
        Initialize an instance of class IllumstatsMetadata.
        '''

    @property
    def channel(self):
        '''
        Returns
        -------
        str
            name of the corresponding channel
        '''
        return self._channel

    @channel.setter
    def channel(self, value):
        self._channel = value

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

    @property
    def files(self):
        '''
        Returns
        -------
        List[str]
            names of the individual image files, which make up the mosaic
        '''
        return self._files

    @files.setter
    def files(self, value):
        self._files = value

    @staticmethod
    def create_from_images(images, layer_name):
        '''
        Create a MosaicMetadata object from image objects.

        Parameters
        ----------
        images: List[ChannelImage]
            set of images that are all of the same *cycle* and *channel*

        Returns
        -------
        MosaicMetadata

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
        metadata = MosaicMetadata()
        metadata.name = layer_name
        metadata.channel = channels[0]
        metadata.sites = [im.site for im in images]
        metadata.cycle = cycles[0]
        metadata.files = [im.name for im in images]
        return metadata
