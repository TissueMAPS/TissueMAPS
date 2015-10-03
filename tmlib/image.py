import re
from abc import ABCMeta
from abc import abstractproperty
from abc import abstractmethod
from cached_property import cached_property
from .pixels import VipsPixels
from .pixels import NumpyPixels
from .readers import DatasetReader
from .errors import MetadataError


SUPPORTED_IMAGE_FILES = ['png']

# A regexp to detect supported files. Used to filter images in a folder_name.
_image_regex = re.compile('.*(' + '|'.join(
    ['\\.' + ext for ext in SUPPORTED_IMAGE_FILES]) + ')$', re.IGNORECASE)


def is_image_file(filename):
    '''
    Check if filename ends with a supported file extension.

    Parameters
    ----------
    filename: str
    '''
    return _image_regex.match(filename)


class Image(object):

    '''
    Abstract base class for an image, which represents a 2D pixels array.

    2D means that the image doesn't contain any z-stacks.
    However, the image array may still have more than 2 dimensions.
    The 3rd dimension represents color and is referred to as "bands".

    The class provides the image pixel array as well as associated metadata.
    It makes use of lazy loading so that image objects can be created without
    the pixels arrays being immediately loaded into memory.
    '''

    __metaclass__ = ABCMeta

    @property
    def metadata(self):
        '''
        Returns
        -------
        Metadata
            metadata object

        See also
        --------
        `tmlib.metadata.ImageMetadata`_
        '''
        return self._metadata

    @metadata.setter
    def metadata(self, value):
        self._metadata = value

    @property
    def filename(self):
        '''
        Returns
        -------
        str
            absolute path to the image file
        '''
        return self._filename

    @filename.setter
    def filename(self, value):
        self._filename = value

    def _get_factory(self, library):
        if library == 'vips':
            return VipsPixels.create_from_file
        elif library == 'numpy':
            return NumpyPixels.create_from_file
        else:
            return None

    @property
    def _factory(self):
        return self.__factory

    @_factory.setter
    def _factory(self, value):
        self.__factory = value

    @abstractproperty
    def pixels(self):
        pass

    @abstractmethod
    @pixels.setter
    def pixels(self, value):
        self._pixels = value

    def save_as_png(self, filename):
        '''
        Write image to disk as PNG file.

        Parameters
        ----------
        filename: str
            absolute path to output file
        '''
        self.pixels.save_as_png(filename)


class ChannelImage(Image):

    '''
    Class for a channel image: a 2D greyscale image with a single band.
    '''

    @staticmethod
    def create_from_file(filename, metadata, library='vips'):
        '''
        Create a ChannelImage object from a file on disk.

        Parameters
        ----------
        filename: str
            absolute path to the image file
        metadata: ChannelImageMetadata
            image metadata object
        library: str, optional
            image library that should be used, "vips" or "numpy"
            (defaults to "vips")

        Returns
        -------
        ChannelImage
            image object

        Raises
        ------
        ValueError
            when `library` is not specified correctly
        '''
        if library not in {'vips', 'numpy'}:
            raise ValueError('Library must be either "vips" or "numpy".')
        image = ChannelImage()
        image._factory = image._get_factory(library)
        image.filename = filename
        image.metadata = metadata
        return image

    @property
    def pixels(self):
        '''
        Returns
        -------
        Pixels
            pixels object

        Raises
        ------
        ValueError
            when `pixels` has more than one band
        TypeError
            when `pixels` doesn't have unsigned integer type

        See also
        --------
        `tmlib.pixels.Pixels`_
        '''
        if hasattr(self, '_factory') and hasattr(self, 'filename'):
            self._pixels = self._factory(self.filename)
        if self._pixels.bands > 1:
            raise ValueError('A channel image can only have a single band.')
        if not self._pixels.is_uint:
            raise TypeError('A channel image must have unsigned integer type.')
        return self._pixels

    @pixels.setter
    def pixels(self, value):
        self._pixels = value

    def correct(self, stats):
        '''
        Correct image for illumination artifacts.

        Parameters
        ----------
        stats: IllumstatsImages
            mean and standard deviation statistics for at each pixel
            calculated over all images of the same channel

        Returns
        -------
        ChannelImage
            a new image object

        Raises
        ------
        ValueError
            when metadata of illumination statistic images and channel image
            do not match
        '''
        if (stats.mean.metadata.channel != self.metadata.channel
                or stats.std.metadata.channel != self.metadata.channel):
            raise ValueError('Channel names must match.')
        if (stats.mean.pixels.type != self.pixels.type
                or stats.std.pixels.type != self.pixels.type):
            raise TypeError('Pixels type must match.')
        new_object = ChannelImage()
        new_object.metadata = self.metadata
        new_object.filename = self.filename
        new_object.pixels = self.pixels.correct_illumination(
                                    stats.mean.pixels.array,
                                    stats.std.pixels.array)
        new_object.metadata.is_corrected = True
        return new_object

    def align(self, crop=True):
        '''
        Align, i.e. shift and crop, an image based on calculated shift
        and overhang values.

        Parameters
        ----------
        crop: bool, optional
            whether images should cropped or rather padded
            with zero valued pixels (default: ``True``)

        Returns
        -------
        ChannelImage
            aligned image

        Warning
        -------
        Alignment may change the dimensions of the image when `crop` is
        ``True``.
        '''
        new_object = ChannelImage()
        new_object.metadata = self.metadata
        new_object.filename = self.filename
        new_object.pixels = self.pixels.align(shift_description=self.metadata,
                                              crop=crop)
        new_object.metadata.is_aligned = True
        return new_object


class BrightfieldImage(Image):

    '''
    Class for a brightfield image: a 2D RGB image with three bands.
    '''

    @staticmethod
    def create_from_file(filename, metadata, library='vips'):
        '''
        Create a BrightfieldImage object from a file on disk.

        Parameters
        ----------
        filename: str
            absolute path to the image file
        metadata: BrightfieldImageMetadata
            image metadata object
        library: str, optional
            image library that should be used, "vips" or "numpy"
            (defaults to "vips")

        Returns
        -------
        BrightfieldImage
            image object

        Raises
        ------
        ValueError
            when `library` is not specified correctly
        '''
        if library not in {'vips', 'numpy'}:
            raise ValueError('Library must be either "vips" or "numpy".')
        image = BrightfieldImage()
        image._factory = image._get_factory(library)
        image.filename = filename
        image.metadata = metadata
        return image

    @property
    def pixels(self):
        '''
        Returns
        -------
        Pixels
            pixels object

        Raises
        ------
        ValueError
            when `pixels` doesn't have three bands
        TypeError
            when `pixels` doesn't have unsigned integer type

        See also
        --------
        `tmlib.pixels.Pixels`_
        '''
        if hasattr(self, '_factory') and hasattr(self, 'filename'):
            self._pixels = self._factory(self.filename)
        if self._pixels.bands != 3:
            raise ValueError('A brightfield image must have 3 bands.')
        if not self._pixels.is_uint:
            raise TypeError('A brightfield image must have unsigned integer '
                            'type.')
        return self._pixels

    @pixels.setter
    def pixels(self, value):
        self._pixels = value


# TODO

class MaskImage(Image):

    '''
    Class for a mask image: a 2D binary segmentation image with a single band.
    '''

    @staticmethod
    def create_from_file(filename, metadata, library='vips'):
        '''
        Create a MaskImage object from a file on disk.

        Parameters
        ----------
        filename: str
            absolute path to the image file
        metadata: SegmentationImageMetadata
            image metadata object
        library: str, optional
            image library that should be used, "vips" or "numpy"
            (defaults to "vips")

        Returns
        -------
        MaskImage
            image object

        Raises
        ------
        ValueError
            when `library` is not specified correctly
        '''
        if library not in {'vips', 'numpy'}:
            raise ValueError('Library must be either "vips" or "numpy".')
        image = MaskImage()
        image._factory = image._get_factory(library)
        image.filename = filename
        image.metadata = metadata
        return image

    @property
    def pixels(self):
        '''
        Returns
        -------
        Pixels
            pixels object

        Raises
        ------
        ValueError
            when `pixels` has more than one band
        TypeError
            when `pixels` doesn't have binary type

        See also
        --------
        `tmlib.pixels.Pixels`_
        '''
        if hasattr(self, '_factory') and hasattr(self, 'filename'):
            self._pixels = self._factory(self.filename)
        if self._pixels.bands > 1:
            raise ValueError('A channel image can only have a single band.')
        if not self._pixels.is_binary:
            raise TypeError('A mask image must have binary type.')
        return self._pixels

    @pixels.setter
    def pixels(self, value):
        self._pixels = value

    @property
    def outlines(self):
        '''
        Returns
        -------
        MaskImage
            non-outline pixels values of connected regions are set to background
        '''
        self._outlines = SegmentationImage(
                            self.pixels.get_outlines(keep_ids=False),
                            self.metadata)
        return self._outlines


class SegmentationImage(Image):

    '''
    Class for a labeled image: a 2D segmentation image,
    where each object (connected component) is labeled with a unique identifier.
    The labeling can be encoded in a single band or in multiple bands
    (which may become necessary when the number of objects exceeds the depth
     of the image, e.g. a greyscale 16-bit image one only encode 2^16 objects).
    '''

    @staticmethod
    def create_from_file(filename, metadata, library='vips'):
        '''
        Create a SegmentationImage object from a file on disk.

        Parameters
        ----------
        filename: str
            absolute path to the image file
        metadata: SegmentationImageMetadata
            image metadata object
        library: str, optional
            image library that should be used, "vips" or "numpy"
            (defaults to "vips")

        Returns
        -------
        SegmentationImage
            image object

        Raises
        ------
        ValueError
            when `library` is not specified correctly
        '''
        if library not in {'vips', 'numpy'}:
            raise ValueError('Library must be either "vips" or "numpy".')
        image = SegmentationImage()
        image._factory = image._get_factory(library)
        image.filename = filename
        image.metadata = metadata
        return image

    @property
    def pixels(self):
        '''
        Returns
        -------
        Pixels
            pixels object

        Raises
        ------
        ValueError
            when `pixels` has not one or three bands
        TypeError
            when `pixels` doesn't have unsigned integer type
        '''
        self._pixels = self._factory(self.filename)
        if self._pixels.bands != 1 or self.pixels.bands != 3:
            raise ValueError('A label image can either have a single band '
                             'or three bands.')
        if not self._pixels.is_uint:
            raise TypeError('A label image must have unsigned integer type.')
        return self._pixels

    @pixels.setter
    def pixels(self, value):
        self._pixels = value

    @property
    def outlines(self):
        '''
        Returns
        -------
        SegmentationImage
            non-outline pixels values of connected regions are set to background
        '''
        self._outlines = SegmentationImage(
                            self.pixels.get_outlines(keep_ids=True),
                            self.metadata)
        return self._outlines

    @property
    def n_objects(self):
        '''
        Returns
        -------
        int
            number of objects in the image
        '''
        self.n_objects = self.pixels.n_objects
        return self._n_objects

    def remove_objects(self, ids):
        '''
        Remove individual objects by their Id.

        Parameters
        ----------
        ids: List[int]
            identifier numbers of objects that should be removed

        Returns
        -------
        SegmentationImage
            image without the specified objects
        '''
        return SegmentationImage(
                    self.pixels.remove_objects(ids), self.metadata)

    def local_to_global_ids(self, max_id):
        '''
        '''
        img, new_max_id = self.pixels.local_to_global_ids(max_id)
        return (SegmentationImage(img, self.metadata), new_max_id)


class IllumstatsImage(object):

    '''
    Class for a illumination statistics image: a 2D greyscale image with a
    single band.
    '''

    def __init__(self, pixels, metadata):
        '''
        Instantiate an instance of class IllumstatsImage.

        Parameters
        ----------
        pixels: Pixel
            pixel object
        metadata: IllumstatsMetadata
            image metadata object

        Returns
        -------
        IllumstatsImage
            image object

        Raises
        ------
        ValueError
            when `pixels` has more than one band
        TypeError
            when `pixels` doesn't have float type
        '''
        self.pixels = pixels
        if self.pixels.bands != 1:
            raise ValueError('An illumination statistics image can only have '
                             'a single band.')
        if not self.pixels.is_float:
            raise TypeError('An illumination statistics image must have '
                            'float type.')
        self.metadata = metadata


class IllumstatsImages(object):

    '''
    Class that serves as a container for illumination statistics images.

    It provides the mean and standard deviation matrices for a given
    channel. The statistics are calculated at each pixel position over all
    image sites acquired in the same channel [1]_.

    References
    ----------
    .. [1] Stoeger T, Battich N, Herrmann MD, Yakimovich Y, Pelkmans L. 2015.
           Computer vision for image-based transcriptomics. Methods.
    '''
    @property
    def filename(self):
        '''
        Returns
        -------
        str
            absolute path to the HDF5 file
        '''
        return self._filename

    @filename.setter
    def filename(self, value):
        self._filename = value

    def _get_factory(self, library):
        if library == 'vips':
            return VipsPixels.create_from_numpy_array
        elif library == 'numpy':
            return NumpyPixels
        else:
            return None

    @property
    def _factory(self):
        return self.__factory

    @_factory.setter
    def _factory(self, value):
        self.__factory = value

    @property
    def std(self):
        '''
        Returns
        -------
        IllumstatsImage
            image object for calculated standard deviation values

        See also
        --------
        `tmlib.image.IllumstatsImage`_ 
        '''
        self._std = self._stats['std']
        return self._std

    @property
    def mean(self):
        '''
        Returns
        -------
        IllumstatsImage
            image object for calculated mean values

        See also
        --------
        `tmlib.image.IllumstatsImage`_
        '''
        self._mean = self._stats['mean']
        return self._mean

    @property
    def metadata(self):
        '''
        Returns
        -------
        IllumstatsMetadata
            metadata object

        See also
        --------
        `tmlib.metadata.IllumstatsMetadata`_
        '''
        return self._metadata

    @metadata.setter
    def metadata(self, value):
        self._metadata = value

    @cached_property
    def _stats(self):
        with DatasetReader(self.filename) as reader:
            mean = self._factory(reader.read('images/mean'))
            std = self._factory(reader.read('images/std'))
            cycle_name = reader.read('metadata/cycle')
            channel_name = reader.read('metadata/channel')
        if cycle_name != self.metadata.cycle:
            raise MetadataError('"cycle" metadata is incorrect')
        if channel_name != self.metadata.channel:
            raise MetadataError('"channel" metadata is incorrect')
        return {
            'mean': IllumstatsImage(pixels=mean, metadata=self.metadata),
            'std': IllumstatsImage(pixels=std, metadata=self.metadata)
        }

    @staticmethod
    def create_from_file(filename, metadata=None, library='vips'):
        '''
        Create an Illumstats object from a file on disk.

        Parameters
        ----------
        filename: str
            absolute path to the HDF5 file
        metadata: IllumstatsMetadata
            metadata object
        library: str, optional
            image library that should be used, "vips" or "numpy"
            (defaults to "vips")

        Returns
        -------
        IllumstatsImages
            container for `IllumstatsImage` objects

        Raises
        ------
        ValueError
            when `library` is not specified correctly
        '''
        if library not in {'vips', 'numpy'}:
            raise ValueError('Library must be either "vips" or "numpy".')
        stats = IllumstatsImages()
        stats.filename = filename
        stats.metadata = metadata
        stats._factory = stats._get_factory(library)
        return stats
