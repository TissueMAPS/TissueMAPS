import re
import os
import mahotas as mh
import numpy as np
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
    Utility class for images.

    It provides the image itself and additional information derived
    from the image filename, such as the position (row/column coordinates)
    of the image within the total imaging acquisition grid, site number,
    cycle number, and name of the corresponding experiment.
    '''

    def __init__(self, filename, cfg):
        '''
        Initialize Image class.

        Parameters
        ----------
        filename: str
            path to the image file
        cfg: Dict[str, str]
            configuration settings

        Raises
        ------
        ValueError
            when file is not a valid image file format
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
        Read image form file and return it as `numpy` array (default -
        if vips set to False) or as `Vips` image (if vips set to True).

        Returns
        -------
        numpy.ndarray or Vips.Image
            image

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
            m = re.search(self.cfg['COORDINATES_FROM_FILENAME'], self.filename)
            if not m:
                raise ValueError('Can\'t determine coordinates from file "%s" '
                                 'using pattern "%s". \n'
                                 'Check your configuration settings!'
                                 % (self.filename,
                                    self.cfg['COORDINATES_FROM_FILENAME']))
            row_nr, col_nr = map(int, m.groups())
            if not self.cfg['COORDINATES_IN_FILENAME_ONE_BASED']:
                row_nr += 1
                col_nr += 1
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
            m = re.search(self.cfg['SITE_FROM_FILENAME'], self.filename)
            if not m:
                raise ValueError('Can\'t determine site from file "%s" '
                                 'using pattern "%s". \n'
                                 'Check your configuration settings!'
                                 % (self.filename,
                                    self.cfg['SITE_FROM_FILENAME']))
            self._site = int(m.group(1))
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
            m = re.search(self.cfg['CYCLE_FROM_FILENAME'], self.filename)
            if not m:
                raise ValueError('Can\'t determine cycle from file "%s" '
                                 'using pattern "%s". \n'
                                 'Check your configuration settings!'
                                 % (self.filename,
                                    self.cfg['CYCLE_FROM_FILENAME']))
            self._cycle = int(m.group(1))
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
            m = re.search(self.cfg['EXPERIMENT_FROM_FILENAME'],
                          os.path.basename(self.filename))
            if not m:
                raise ValueError('Can\'t determine experiment from file "%s" '
                                 'using pattern "%s". \n'
                                 'Check your configuration settings!'
                                 % (self.filename,
                                    self.cfg['EXPERIMENT_FROM_FILENAME']))
            self._experiment = m.group(1)
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


class IntensityImage(Image):
    '''
    Utility class for an intensity image,
    i.e. a two dimensional gray-scale image.

    It provides the image itself (as type float)
    and additional information derived from the image filename,
    such as the channel number.
    '''

    def __init__(self, filename, cfg):
        Image.__init__(self, filename, cfg)
        self.filename = filename
        self.cfg = cfg
        self.use_vips = cfg['USE_VIPS_LIBRARY']
        self._channel = None

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
            m = re.search(self.cfg['CHANNEL_FROM_FILENAME'], self.filename)
            if not m:
                raise ValueError('Can\'t determine channel from file "%s" '
                                 'using pattern "%s". \n'
                                 'Check your configuration settings!'
                                 % (self.filename,
                                    self.cfg['CHANNEL_FROM_FILENAME']))
            self._channel = int(m.group(1))
        return self._channel


class MaskImage(Image):
    '''
    Utility class for a mask image,
    i.e. a two dimensional labeled image that represents
    segmented objects as a continuous region of identical pixel values > 0.
    The list of unique pixels values are also referred to as the objects IDs.

    It provides the image itself and additional information derived
    from the image filename, such as the name of objects encoded in the image
    and their unique ids.
    '''
    def __init__(self, filename, cfg):
        Image.__init__(self, filename, cfg)
        self.filename = filename
        self.cfg = cfg
        self.use_vips = cfg['USE_VIPS_LIBRARY']
        self._objects = None
        self._ids = None

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
            m = re.search(self.cfg['OBJECTS_FROM_FILENAME'], self.filename)
            if not m:
                raise ValueError('Can\'t determine objects from file "%s" '
                                 'using pattern "%s". \n'
                                 'Check your configuration settings!'
                                 % (self.filename,
                                    self.cfg['OBJECTS_FROM_FILENAME']))
            self._objects = m.group(1)
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
    # as iterable object
