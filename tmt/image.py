import re
import os
import mahotas as mh
from scipy import misc
import numpy as np
import utils
try:
    from gi.repository import Vips
except ImportError as error:
    print 'Vips could not be imported.\nReason: %s' % str(error)


SUPPORTED_IMAGE_FILES = ['png', 'jpg', 'tiff', 'jpeg']

# A regexp to detect supported files. Used to filter images in a folder_name.
_image_regex = re.compile('.*(' + '|'.join(
    ['\\.' + ext for ext in SUPPORTED_IMAGE_FILES]) + ')$', re.IGNORECASE)


def is_image_file(filename):
    '''
    Check if filename ends with a supported file extension.

    Parameters
    ----------
    filename: str
        name of the image file
    '''
    return _image_regex.match(filename)


class Image(object):
    '''
    Utility class for an image.

    It provides the image itself and additional meta-information derived
    from the image filename or a provided by the user, such as the position
    (row/column coordinates) of the image within the total imaging acquisition
    grid, site number, cycle number, and name of the corresponding experiment.
    '''

    def __init__(self, filename, cfg, info):
        '''
        Initialize instance of class Image.

        Parameters
        ----------
        filename: str
            path to the image file
        cfg: Dict[str, str]
            configuration settings
        info: Dict[str, str or int], optional
            information about image files, such as positional information
            within the acquisition grid

        Raises
        ------
        ValueError
            when `filename` is not a valid image file format or
            when `info` is not provided, but would be required
        '''
        self.cfg = cfg
        if not os.path.isabs(filename):
            self.filename = os.path.abspath(filename)
        else:
            self.filename = filename
        if not is_image_file(self.filename):
            raise ValueError('File "%s" is not a supported image file format. '
                             'Supported formats are: %s '
                             % (self.filename,
                                SUPPORTED_IMAGE_FILES.join(', ')))
        # NOTE: We only check whether the image file actually exists when
        # we try to load the image. This still allows us to extract information
        # from filenames for which no absolute path is available.
        self.use_vips = self.cfg['USE_VIPS_LIBRARY']
        self.info_from_filename = self.cfg['IMAGE_INFO_FROM_FILENAME']
        self.info = info
        if not self.cfg['IMAGE_INFO_FROM_FILENAME'] and self.info is None:
            raise ValueError('IMAGE_INFO_FROM_FILENAME is set to False in '
                             'configuration settings, but no information '
                             'is provided.')
        self._image = None
        self._dimensions = None
        self._coordinates = None
        self._indices = None
        self._site = None
        self._cycle = None
        self._channel = None
        self._experiment = None
        self._experiment_dir = None

    @property
    def named_regex_string(self):
        '''
        Returns
        -------
        str
            named regular expression string built from format string
            "IMAGE_FILE_FORMAT" defined in the `tmt.config`_ file

        See also
        --------
        `utils.regex_from_format_string`
        '''
        string = utils.regex_from_format_string(self.cfg['IMAGE_FILE_FORMAT'])
        self._named_regex_string = string
        return self._named_regex_string

    @property
    def metadata(self):
        '''
        Returns
        -------
        Dict[str, int]
            metadata for an image filename: "site", "row", "column", and
            "cycle" number
        '''
        if self._metadata is None and self.info:
            self._metadata = self.info[self.filename]
        return self._metadata

    @property
    def name(self):
        '''
        Returns
        -------
        str
            basename of the image file
        '''
        self._name = os.path.basename(self.filename)
        return self._name

    @property
    def image(self):
        '''
        Read image form file and return it as `ndarray`
        (if `USE_VIPS_LIBRARY` is set to False) or as `VipsImage` otherwise.

        Returns
        -------
        numpy.ndarray or Vips.Image
            loaded image

        Raises
        ------
        OSError
            when image file does not exist on disk
        '''
        if self._image is None:
            if not os.path.exists(self.filename):
                raise OSError('Cannot load image because '
                              'file "%s" does not exist.' % self.filename)
            if self.use_vips:
                self._image = Vips.Image.new_from_file(self.filename)
            else:
                self._image = mh.imread(self.filename)
        return self._image

    @property
    def dimensions(self):
        '''
        Returns
        -------
        Tuple[int]
            y, x dimensions (height, width) of the image
        '''
        if self._dimensions is None:
            if self.use_vips:
                self._dimensions = (self.image.height, self.image.width)
            else:
                self._dimensions = self.image.shape
        return self._dimensions

    @property
    def coordinates(self):
        '''
        Returns
        -------
        Tuple[int]
            one-based row, column coordinates of an image
            relative to the acquisition grid in 2D, determined from filename
            using regular expression pattern provided in configuration settings

        Raises
        ------
        ValueError
            when coordinates cannot not be determined from filename
        '''
        if not self._coordinates:
            if self.info_from_filename:
                m = re.search(self.named_regex_string, self.filename)
                if not m:
                    raise ValueError('Can\'t determine coordinates from '
                                     'filename "%s" using format string "%s".'
                                     '\nCheck your configuration settings!'
                                     % (self.filename,
                                        self.cfg['IMAGE_FILE_FORMAT']))
                row_nr = int(m.group('row'))
                col_nr = int(m.group('column'))
                if not self.cfg['COORDINATES_IN_FILENAME_ONE_BASED']:
                    row_nr += 1
                    col_nr += 1
            else:
                row_nr = self.metadata['row']
                col_nr = self.metadata['column']
            self.row = row_nr
            self.column = col_nr
            self._coordinates = (row_nr, col_nr)
        return self._coordinates

    @property
    def indices(self):
        '''
        Returns
        -------
        Tuple[int]
            zero-based row, column coordinates of an image
            relative to the acquisition grid in 2D, determined from filename
            using regular expression pattern provided in configuration settings
        '''
        if self._indices is None:
            row_nr, col_nr = self.coordinates
            if self.cfg['COORDINATES_IN_FILENAME_ONE_BASED']:
                row_nr -= 1
                col_nr -= 1
            self._indices = (row_nr, col_nr)
        return self._indices

    @property
    def site(self):
        '''
        Returns
        -------
        int
            one-based site number of an image, determined from filename
            using regular expression pattern provided in configuration settings

        Raises
        ------
        ValueError
            when site number cannot not be determined from filename
        '''
        if self._site is None:
            if self.info_from_filename:
                m = re.search(self.named_regex_string, self.filename)
                if not m:
                    raise ValueError('Can\'t determine site from filename "%s" '
                                     'using format string "%s".'
                                     '\nCheck your configuration settings!'
                                     % (self.filename,
                                        self.cfg['IMAGE_FILE_FORMAT']))
                self._site = int(m.group('site'))
            else:
                self._site = self.metadata['site']
        return self._site

    @property
    def cycle(self):
        '''
        Returns
        -------
        int
            one-based cycle number of an image, determined from filename
            using regular expression pattern provided in configuration settings

        Raises
        ------
        ValueError
            when cycle number cannot not be determined from filename
        '''
        if self._cycle is None:
            if self.info_from_filename:
                m = re.search(self.named_regex_string, self.filename)
                if not m:
                    raise ValueError('Can\'t determine cycle from '
                                     'filename "%s" using format string "%s".'
                                     '\nCheck your configuration settings!'
                                     % (self.filename,
                                        self.cfg['IMAGE_FILE_FORMAT']))
                self._cycle = int(m.group('cycle'))
            else:
                self._cycle = self.metadata['cycle']
        return self._cycle

    @property
    def experiment(self):
        '''
        Returns
        -------
        str
            experiment name, determined from filename
            using regular expression pattern provided in configuration settings

        Raises
        ------
        ValueError
            when experiment name cannot not be determined from filename
        '''
        if self._experiment is None:
            if self.info_from_filename:
                m = re.search(self.named_regex_string,
                              os.path.basename(self.filename))
                if not m:
                    raise ValueError('Can\'t determine experiment from '
                                     'filename "%s" using format string "%s".'
                                     '\nCheck your configuration settings!'
                                     % (self.filename,
                                        self.cfg['IMAGE_FILE_FORMAT']))
                self._experiment = m.group(1)
            else:
                # TODO: wouldn't it be better to always use this approach?
                self._experiment = os.path.basename(self.experiment_dir)
        return self._experiment

    @property
    def experiment_dir(self):
        '''
        Returns
        -------
        str
            path to experiment directory, determined from filename
        '''
        if self._experiment_dir is None:
            if self.cfg['SUBEXPERIMENTS_EXIST']:
                levels = 2
            else:
                levels = 1
            self._experiment_dir = os.path.realpath(os.path.join(
                                        os.path.dirname(self.filename),
                                        * ['..'] * levels))
        return self._experiment_dir


class ChannelImage(Image):
    '''
    Utility class for a channel image,
    i.e. a two dimensional gray-scale image.

    It provides the image itself (as type float)
    and additional information derived from the image filename or
    provided by the user, such as the channel number.

    See also
    --------
    `Image`_
    '''

    def __init__(self, filename, cfg, info=None):
        '''
        Initialize instance of class ChannelImage.

        Parameters
        ----------
        filename: str
            path to the image file
        cfg: Dict[str, str]
            configuration settings
        info: Dict[str, str or int], optional
            information about image files, such as positional information
            within the acquisition grid

        Raises
        ------
        ValueError
            when `filename` is not a valid image file format or
            when `info` is not provided, but would be required
        '''
        Image.__init__(self, filename, cfg, info)
        self.filename = filename
        self.cfg = cfg
        self.use_vips = cfg['USE_VIPS_LIBRARY']
        self.info = info
        self._metadata = None
        self._channel = None

    @property
    def metadata(self):
        '''
        Returns
        -------
        Dict[str, int]
            metadata for an image filename: "site", "row", "column", cycle",
            and "channel" number
        '''
        if self._metadata is None:
            self._metadata = self.info[self.filename]
        return self._metadata

    @property
    def channel(self):
        '''
        Returns
        -------
        int
            channel number, determined from filename
            using regular expression pattern provided in configuration settings

        Raises
        ------
        ValueError
            when channel number cannot be determined from filename
        '''
        if self._channel is None:
            if self.info_from_filename:
                m = re.search(self.named_regex_string, self.filename)
                if not m:
                    raise ValueError('Can\'t determine channel from '
                                     'filename "%s" using format string "%s".'
                                     '\nCheck your configuration settings!'
                                     % (self.filename,
                                        self.cfg['IMAGE_FILE_FORMAT']))
                self._channel = int(m.group('channel'))
            else:
                self._channel = self.metadata['channel']
        return self._channel

    @property
    def image(self):
        '''
        Read image form file and return it as `ndarray`
        (if `USE_VIPS_LIBRARY` is set to False) or as `VipsImage` otherwise.

        Returns
        -------
        numpy.ndarray[float64] or Vips.Image[double]
            image

        Raises
        ------
        OSError
            when image file does not exist on disk
        '''
        f = self.filename
        if self._image is None:
            if not os.path.exists(self.filename):
                raise OSError('Cannot load image because '
                              'file "%s" does not exist.' % self.filename)
            if self.use_vips:
                self._image = Vips.Image.new_from_file(f).cast('double')
            else:
                self._image = np.array(misc.imread(f), dtype='float64')
        return self._image


class SegmentationImage(Image):
    '''
    Utility class for a segmentation image,
    i.e. a two dimensional labeled image that represents
    segmented objects as a continuous region of identical pixel values > 0.
    The list of unique pixels values are also referred to as the objects IDs.

    It provides the image itself and additional information derived
    from the image filename or provided by the user, such as the name
    of objects encoded in the image and their unique ids.

    See also
    --------
    `Image`_
    '''
    def __init__(self, filename, cfg, info):
        '''
        Initialize instance of class SegmentationImage.

        Parameters
        ----------
        filename: str
            path to the image file
        cfg: Dict[str, str]
            configuration settings
        info: Dict[str, str or int], optional
            information about image files, such as positional information
            within the acquisition grid

        Raises
        ------
        ValueError
            when `filename` is not a valid image file format or
            when `info` is not provided, but would be required
        '''
        Image.__init__(self, filename, cfg, info)
        self.filename = filename
        self.cfg = cfg
        self.use_vips = cfg['USE_VIPS_LIBRARY']
        self.info = info
        self._metadata = None
        self._objects = None
        self._ids = None

    @property
    def named_regex_string(self):
        '''
        Returns
        -------
        str
            named regular expression string built from format string
            "SEGMENTATION_FILE_FORMAT" defined in the `tmt.config`_ file

        See also
        --------
        `utils.regex_from_format_string`_
        '''
        string = utils.regex_from_format_string(self.cfg['SEGMENTATION_FILE_FORMAT'])
        self._named_regex_string = string
        return self._named_regex_string

    @property
    def metadata(self):
        '''
        Returns
        -------
        Dict[str, int]
            metadata for an image filename: "site", "row", "column", and cycle"
            number and "objects" name
        '''
        if self._metadata is None:
            self._metadata = self.info[self.filename]
        return self._metadata

    @property
    def name(self):
        '''
        Returns
        -------
        str
            basename of the image file
        '''
        self._name = os.path.basename(self.filename)
        return self._name

    @property
    def objects(self):
        '''
        Returns
        -------
        str
            name of objects in the mask image, determined from filename
            using regular expression pattern provided in configuration settings

        Raises
        ------
        ValueError
            when objects name cannot not be determined from filename
        '''
        if self._objects is None:
            if self.info_from_filename:
                m = re.search(self.named_regex_string, self.filename)
                if not m:
                    raise ValueError('Can\'t determine objects from '
                                     'filename "%s" using format string "%s".'
                                     '\nCheck your configuration settings!'
                                     % (self.filename,
                                        self.cfg['SEGMENTATION_FILE_FORMAT']))
                self._objects = m.group('objects')
            else:
                self._objects = self.metadata['objects']
        return self._objects

    @property
    def ids(self):
        '''
        Returns
        -------
        List[int]
        unique ids of objects in the mask image
        '''
        if self._ids is None:
            if self.use_vips:
                num_labels = int(self.image.max())
                values = range(1, num_labels+1)
            else:
                num_labels = int(np.max(self.image))
                values = range(1, num_labels+1)
            self._ids = values
        return self._ids

    # TODO:
    # add methods for providing the sub-images (from bounding boxes)
    # as iterable object?
