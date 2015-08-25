from abc import ABCMeta
from abc import abstractmethod
import cv2
import sys
import traceback
from gi.repository import Vips
import bioformats as bf
import javabridge


class ImageReader(object):

    '''
    Abstract base class for reading images from files on disk.
    '''

    __metaclass__ = ABCMeta

    def __enter__(self):
        return self

    @abstractmethod
    def read(self, filename):
        pass

    @abstractmethod
    def read_subset(self, filename, series_index=None, plane_index=None):
        pass

    def __exit__(self, except_type, except_value, except_trace):
        pass


class BioformatsImageReader(ImageReader):

    '''
    Class for reading images using the
    `Bio-Formats <http://www.openmicroscopy.org/site/products/bio-formats>`_
    library.

    Raises
    ------
    NotImplementedError
        when the file format is not supported by the reader

    Examples
    --------
    >>> filename = '/path/to/image/file'
    >>> with BioformatsImageReader() as reader:
    ...     img = reader.read(filename)
    >>> type(img)
    numpy.ndarray
    '''

    def __enter__(self):
        # NOTE: updated "loci_tools.jar" file to latest schema:
        # http://downloads.openmicroscopy.org/bio-formats/5.1.3
        javabridge.start_vm(class_path=bf.JARS, run_headless=True)
        return self

    def read(self, filename):
        '''
        Read an image from a file on disk.

        For details on reading images via Bio-Format from Python, see
        `load_image() <http://pythonhosted.org/python-bioformats/#reading-images>`_.

        Unfortunately, the documentation is very sparse and sometimes wrong.
        If you need additional information, refer to the relevant
        `source code <https://github.com/CellProfiler/python-bioformats/blob/master/bioformats/formatreader.py>`_.

        Parameters
        ----------
        filename: str
            absolute path to the image file

        Returns
        -------
        numpy.ndarray
            image pixel array
        '''
        image = bf.load_image(filename, rescale=False)
        return image

    def read_subset(self, filename, series_index=None, plane_index=None):
        '''
        Read a subset of images from a file on disk.

        Parameters
        ----------
        filename: str
            absolute path to the image file
        series_index: int, optional
            zero-based index of the image in the series of images
            (only relevant if the file contains more than one Image elements)
        plane_index: int, optional
            zero-based index of the image in a plane
            (only relevant if the file contains at least one Plane element
             with more than one Pixels element)

        Returns
        -------
        numpy.ndarray
            image pixel array
        '''
        image = bf.load_image(filename, rescale=False,
                              series=series_index, index=plane_index)
        return image

    def __exit__(self, except_type, except_value, except_trace):
        javabridge.kill_vm()
        if except_type is javabridge.JavaException:
            raise NotImplementedError('File format is not supported.')
        if except_value:
            sys.stdout.write('The following error occurred:\n%s'
                             % str(except_value))
            for tb in traceback.format_tb(except_trace):
                sys.stdout.write(tb)


class OpencvImageReader(ImageReader):

    '''
    Class for reading image using the `OpenCV <http://docs.opencv.org>`_
    library.

    Examples
    --------
    >>> filename = '/path/to/image/file'
    >>> with OpencvReader() as reader:
    ...     img = reader.read(filename)
    >>> type(img)
    numpy.ndarray
    '''

    def read(self, filename):
        '''
        Read an image from file on disk.

        For details on reading image via OpenCV from Python, see
        `imread() <http://docs.opencv.org/modules/highgui/doc/reading_and_writing_images_and_video.html#imread>`_

        Parameters
        ----------
        filename: str
            absolute path to the file

        Returns
        -------
        numpy.array
            image pixel array
        '''
        image = cv2.imread(filename, cv2.IMREAD_UNCHANGED)
        return image

    def read_subset(self, filename,
                    series_index=None, plane_index=None):
        '''
        If the image file contains more than one plane (band), only the first
        one will be read.
        '''
        raise AttributeError('%s doesn\'t have a "read_subset" method'
                             % self.__class__.__name__)


class VipsImageReader(ImageReader):

    '''
    Class for reading images using the
    `Vips <http://www.vips.ecs.soton.ac.uk/index.php?title=Libvips>`_ library.

    Examples
    --------
    >>> filename = '/path/to/image/file'
    >>> with VipsReader() as reader:
    ...     img = reader.read(filename)
    >>> type(img)
    Vips.Image
    '''

    def read(self, filename):
        '''
        Read an image from file on disk.

        For details on reading images via VIPS from Python, see
        `new_from_file() <http://www.vips.ecs.soton.ac.uk/supported/current/doc/html/libvips/using-from-python.html>`_

        Parameters
        ----------
        filename: str
            absolute path to the file

        Returns
        -------
        Vips.Image
            image pixel array
        '''
        image = Vips.Image.new_from_file(filename)
        return image

    def read_subset(self, filename, series_index=None, plane_index=None):
        raise AttributeError('%s doesn\'t have a "read_subset" method. '
                             'If the file contains more than one plane/band, '
                             'only the first one will be read.'
                             % self.__class__.__name__)


class OpenslideImageReader(ImageReader):

    '''
    Class for reading whole slide images and associated metadata using the
    `Openslide <http://openslide.org/>`_ library.

    Raises
    ------
    NotImplementedError
        when the file format is not supported by the reader

    Examples
    --------
    >>> filename = '/path/to/image/file'
    >>> with OpenslideReader() as reader:
    ...     img = reader.read(filename)
    ...     metadata = reader.read_metadata(filename)
    >>> type(img)
    Vips.Image
    >>> type(img)
    openslide.OpenSlide
    '''

    def read(self, filename):
        '''
        Read highest resolution level of a whole slide image from disk.

        For details on reading whole slide images via Vips from Python, see
        `vips_openslideload() <http://www.vips.ecs.soton.ac.uk/supported/current/doc/html/libvips/VipsForeignSave.html#vips-openslideload>`_.

        Parameters
        ----------
        filename: str
            absolute path to the file

        Returns
        -------
        Vips.Image
            image pixel array
        '''
        image = Vips.Image.openslideload(filename, level=0)
        return image

    def read_subset(self, filename, series_index=None, plane_index=None):
        raise AttributeError('%s doesn\'t have a "read_subset" method. '
                             'If the file contains more than one plane/band, '
                             'only the first one will be read.'
                             % self.__class__.__name__)
