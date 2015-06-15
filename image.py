import re
from os.path import join, dirname, realpath, exists, isabs, abspath, basename
import mahotas as mh
import numpy as np
from gi.repository import Vips


SUPPORTED_IMAGE_FILES = ['png', 'jpg', 'tiff', 'jpeg']

# A regexp to detect supported files. Used to filter images in a folder_name.
_image_regex = re.compile('.*(' + '|'.join(
    ['\\.' + ext for ext in SUPPORTED_IMAGE_FILES]) + ')$', re.IGNORECASE)


def is_image_file(filename):
    '''Check if filename ends with a supported file extension'''
    return _image_regex.match(filename)


class Image(object):
    '''Utility class for an image.
    The class provides the image itself and additional information derived
    from the image filename, such as the position (row/column coordinates)
    of the image within the total imaging acquisition grid (zero based!),
    site number, cycle number, and name of the corresponding experiment.
    '''

    def __init__(self, filename, cfg, vips=False):
        '''
        Initialize Image class.

        Parameters:
        :filename:      Path to the image file : str.
        :cfg:           Configuration settings : dict.
        '''
        self.cfg = cfg
        if not isabs(filename):
            self.filename = abspath(filename)
        else:
            self.filename = filename
        if not is_image_file(self.filename):
            raise Exception('File "%s" is not a supported image file.' %
                            self.filename)
        # NOTE: We only check whether the image file actually exists when
        # we try to load the image. This allows us to extract information
        # from filenames for which no absolute path is available.
        self.vips = vips
        self._image = None
        self._image_vips = None
        self._dimensions = None
        self._coordinates = None
        self._indices = None
        self._site = None
        self._cycle = None
        self._channel = None
        self._experiment = None
        self._experiment_dir = None

    @property
    def image(self):
        '''
        Read image form file and return it as numpy array (default)
        or as Vips object if vips set to True.
        '''
        if self._image is None:
            if not exists(self.filename):
                raise Exception('Cannot load image because '
                                'file "%s" does not exist.' % self.filename)
            if self.vips:
                self._image = Vips.Image.new_from_file(self.filename)
            else:
                self._image = mh.imread(self.filename)
        return self._image

    @property
    def dimensions(self):
        '''
        Return the y, x dimensions of the image as tuple.
        '''
        if self._dimensions is None:
            if self.vips:
                # TODO: check Y and X used correctly
                self._dimensions = (self._image.width, self._image.height)
            else:
                self._dimensions = self._image.shape
        return self._dimensions

    @property
    def coordinates(self):
        '''
        Return one-based row, column coordinates of an image
        relative to the acquisition grid.
        '''
        if not self._coordinates:
            m = re.search(self.cfg['COORDINATES_FROM_FILENAME'], self.filename)
            if not m:
                raise Exception('Can\'t determine coordinates from file "%s"'
                                % self.filename)
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
        Return zero-based row, column indices of an image
        relative to the acquisition grid.
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
        Return one-based site number of an image
        relative to the acquisition sequence over time.
        '''
        if self._site is None:
            m = re.search(self.cfg['SITE_FROM_FILENAME'], self.filename)
            if not m:
                raise Exception('Can\'t determine site from file "%s"'
                                % self.filename)
            self._site = int(m.group(1))
        return self._site

    @property
    def cycle(self):
        '''
        Return one-based cycle number of an image.
        '''
        if self._cycle is None:
            m = re.search(self.cfg['CYCLE_FROM_FILENAME'], self.filename)
            if not m:
                raise Exception('Can\'t determine cycle from file "%s"'
                                % self.filename)
            self._cycle = int(m.group(1))
        return self._cycle

    @property
    def experiment(self):  # get_expname_from_filename()
        '''
        Return experiment name.
        '''
        if self._experiment is None:
            m = re.search(self.cfg['EXPERIMENT_FROM_FILENAME'],
                          basename(self.filename))
            if not m:
                raise Exception('Can\'t determine experiment from file "%s"'
                                % self.filename)
            self._experiment = m.group(1)
        return self._experiment

    @property
    def experiment_dir(self):
        '''
        Return path to the experiment folder.
        '''
        if self._experiment_dir is None:
            if self.cfg['SUBEXPERIMENTS_EXIST']:
                levels = 2
            else:
                levels = 1
            self._experiment_dir = realpath(join(dirname(self.filename),
                                                 * ['..'] * levels))
        return self._experiment_dir


class IntensityImage(Image):
    '''Utility class for an intensity image.
    An intensity image is a two dimensional gray-scale image.
    The class provides the image itself (type float!)
    and additional information derived from the image filename,
    such as the channel number.
    '''

    # TODO: vips

    def __init__(self, filename, cfg, vips=False):
        Image.__init__(self, filename, cfg, vips=False)
        self.filename = filename
        self.cfg = cfg
        self.vips = vips
        self._channel = None

    @property
    def image(self):
        '''
        Read image form file and return it as numpy array of type float.
        '''
        if self._image is None:
            if self.vips:
                self._image = Vips.Image.new_from_file(self.filename)
            else:
                self._image = mh.imread(self.filename).astype(float)
        return self._image

    @property
    def channel(self):  # get_channel_nr_from_filename()
        if self._channel is None:
            m = re.search(self.cfg['CHANNEL_FROM_FILENAME'], self.filename)
            if not m:
                raise Exception('Can\'t determine channel from file "%s"'
                                % self.filename)
            self._channel = int(m.group(1))
        return self._channel


class MaskImage(Image):
    '''Utility class for a mask image.
    A mask image is a two dimensional labeled image that represents
    segmented objects as a continuous region of identical pixel values > 0.
    The list of unique pixels values are also referred to as the objects IDs.
    The class provides the image itself and additional information derived
    from the image filename, such as the name of objects encoded in the image
    and their unique ids.
    '''
    def __init__(self, filename, cfg):
        Image.__init__(self, filename, cfg)
        self.filename = filename
        self.cfg = cfg
        self._objects = None
        self._ids = None

    @property
    def objects(self):
        if self._objects is None:
            m = re.search(self.cfg['OBJECT_FROM_FILENAME'], self.filename)
            if not m:
                raise Exception('Can\'t determine object from file "%s"'
                                % self.filename)
            self._objects = m.group(1)
        return self._objects

    @property
    def ids(self):
        if self._ids is None:
            values = np.unique(self._image)
            self._ids = filter(np.nonzero, values)  # remove 0 background
        return self._ids

    # TODO:
    # include more methods for providing the sub-images (from bounding boxes)
    # as iterable object
