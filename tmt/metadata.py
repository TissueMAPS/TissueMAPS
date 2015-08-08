class ImageMetadata(object):

    '''
    A base class for holding metadata about an image, such as the
    position of the image in the acquisition grid.
    '''

    def __init__(self, metadata, cycle=1):
        '''
        Initialize an instance of class Metadata.

        Parameters
        ----------
        metadata: Dict[str, int or str]
            metadata read from the *.metadata* YAML file
        cycle: int, optional
            one-based cycle index (defaults to 1)
        '''
        self.metadata = metadata
        self.cycle = cycle

    @property
    def filename(self):
        '''
        Returns
        -------
        str
            name of the corresponding image file

        Raises
        ------
        KeyError
            when `metadata` doesn't contain "filename" information
        '''
        if 'filename' not in self.metadata:
            raise KeyError('Metadata must contain "filename" information')
        self._filename = self.metadata['filename']
        return self._filename

    @property
    def site(self):
        '''
        Returns
        -------
        int
            zero-based index of the image in the acquisition sequence

        Raises
        ------
        KeyError
            when `metadata` doesn't contain "site" information
        '''
        if 'site' not in self.metadata:
            raise KeyError('Metadata must contain "site" information')
        self._site = self.metadata['site']
        return self._site

    @property
    def row(self):
        '''
        Returns
        -------
        int
            zero-based row index of the image in the acquisition grid

        Raises
        ------
        KeyError
            when `metadata` doesn't contain "row" information
        '''
        if 'row' not in self.metadata:
            raise KeyError('Metadata must contain "row" information')
        self._row = self.metadata['row']
        return self._row

    @property
    def column(self):
        '''
        Returns
        -------
        int
            zero-based column index of the image in the acquisition grid

        Raises
        ------
        KeyError
            when `metadata` doesn't contain "column" information
        '''
        if 'column' not in self.metadata:
            raise KeyError('Metadata must contain "column" information')
        self._column = self.metadata['column']
        return self._column

    @property
    def coordinates(self):
        '''
        Returns
        -------
        Tuple[int]
            zero-based row, column indices of the image in the acquisition grid
        '''
        self._coordinates = (self.row, self.column)
        return self._coordinates

    @property
    def well_position(self):
        '''
        Returns
        -------
        Tuple[int]
            zero-based row, column indices of the well in the plate
        '''
        if 'well_position' in self.metadata:
            self._well_position = self.metadata['well_position']
        else:
            self._well = tuple()
        return self._well_position

    @property
    def well(self):
        '''
        Returns
        -------
        str
            name given to a well in the multi-well plate
        '''
        if 'well' in self.metadata:
            self._well = self.metadata['well']
        else:
            self._well = ''
        return self._well


class ChannelMetadata(ImageMetadata):

    def __init__(self, metadata, cycle=1):
        '''
        Initialize an instance of class ChannelMetadata.

        Parameters
        ----------
        metadata: Dict[str, int or str]
            metadata read from the *.metadata* YAML file
        cycle: int, optional
            one-based cycle index (defaults to 1)
        '''
        ImageMetadata.__init__(self, metadata, cycle)
        self.metadata = metadata
        self.cycle = cycle

    @property
    def channel(self):
        '''
        Returns
        -------
        str
            name given to the channel

        Raises
        ------
        KeyError
            when `metadata` doesn't contain "channel" information
        '''
        if 'channel' not in self.metadata:
            raise KeyError('Metadata must contain "channel" information')
        self._channel = self.metadata['channel']
        return self._channel


class SegmentationMetadata(ImageMetadata):

    def __init__(self, metadata, cycle=1):
        '''
        Initialize an instance of class SegmentationMetadata.

        Parameters
        ----------
        metadata: Dict[str, int or str]
            metadata read from the *.metadata* YAML file
        cycle: int, optional
            one-based cycle index (defaults to 1)
        '''
        ImageMetadata.__init__(self, metadata, cycle)
        self.metadata = metadata
        self.cycle = cycle

    @property
    def objects(self):
        '''
        Returns
        -------
        str
            name given to the objects in the image

        Raises
        ------
        KeyError
            when `metadata` doesn't contain "objects' information
        '''
        if 'objects' not in self.metadata:
            raise KeyError('Metadata must contain "objects' information')
        self._objects = self.metadata['objects']
        return self._objects
