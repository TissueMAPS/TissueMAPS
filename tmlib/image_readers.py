import os
import cv2
from gi.repository import Vips
import sys
import traceback
import bioformats
import javabridge
import logging
from .readers import ImageReader
from .readers import SlideReader
from .errors import NotSupportedError

logger = logging.getLogger(__name__)


class BioformatsImageReader(ImageReader):

    '''
    Class for reading images using the
    `Bio-Formats <http://www.openmicroscopy.org/site/products/bio-formats>`_
    library.

    Note
    ----
    Requires a running Java Virtual Machine (VM). This is achieved via the
    `javabridge <http://pythonhosted.org/javabridge/start_kill.html>`_
    package.

    Warning
    -------
    Once the VM is killed it cannot be started again. This means that a second
    call of this class will fail.

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
        javabridge.start_vm(class_path=bioformats.JARS, run_headless=True)
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

        Raises
        ------
        OSError
            when `filename` does not exist
        NotSupportedError
            when the file format is not supported by the reader

        Returns
        -------
        numpy.ndarray
            pixel array
        '''
        if not os.path.exists(filename):
            raise OSError('Image file does not exist: %s' % filename)
        image = bioformats.load_image(filename, rescale=False)
        return image

    def read_subset(self, filename, series=None, plane=None):
        '''
        Read a subset of images from a file on disk.

        Parameters
        ----------
        filename: str
            absolute path to the image file
        series: int, optional
            zero-based series index
            (only relevant if the file contains more than one *Image* elements)
        plane: int, optional
            zero-based plane index within a series
            (only relevant if *Image* elements within the file contain 
             more than one *Plane* element)

        Returns
        -------
        numpy.ndarray
            2D pixel array

        Raises
        ------
        OSError
            when `filename` does not exist
        NotSupportedError
            when the file format is not supported by the reader
        '''
        if not os.path.exists(filename):
            raise OSError('Image file does not exist: %s' % filename)
        image = bioformats.load_image(filename, rescale=False,
                                      series=series, index=plane)
        return image

    def __exit__(self, except_type, except_value, except_trace):
        javabridge.kill_vm()
        if except_type is javabridge.JavaException:
            raise NotSupportedError('File format is not supported.')
        if except_value:
            sys.stdout.write('The following error occurred:\n%s'
                             % str(except_value))
            for tb in traceback.format_tb(except_trace):
                sys.stdout.write(tb)


class OpencvImageReader(ImageReader):

    '''
    Class for reading images using the `OpenCV <http://docs.opencv.org>`_
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

        Raises
        ------
        OSError
            when `filename` does not exist
        '''
        if not os.path.exists(filename):
            raise OSError('Image file does not exist: %s' % filename)
        image = cv2.imread(filename, cv2.IMREAD_UNCHANGED)
        return image

    def read_subset(self, filename, series=None, plane=None):
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

        Raises
        ------
        OSError
            when `filename` does not exist
        '''
        if not os.path.exists(filename):
            raise OSError('Image file does not exist: %s' % filename)
        image = Vips.Image.new_from_file(filename)
        return image

    def read_subset(self, filename, series=None, plane=None):
        raise AttributeError('%s doesn\'t have a "read_subset" method. '
                             'If the file contains more than one plane/band, '
                             'only the first one will be read.'
                             % self.__class__.__name__)


class OpenslideImageReader(SlideReader):

    '''
    Class for reading whole slide images and associated metadata using the
    `Openslide <http://openslide.org/>`_ library.

    Raises
    ------
    NotSupportedError
        when the file format is not supported by the reader

    Warning
    -------
    `Openslide` doesn't support fluorescence slides.

    Examples
    --------
    >>> filename = '/path/to/image/file'
    >>> with OpenslideReader() as reader:
    ...     img = reader.read(filename)
    >>> type(img)
    Vips.Image
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

