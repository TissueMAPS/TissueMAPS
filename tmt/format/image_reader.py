import sys
import traceback
import bioformats as bf
import javabridge
from .. image_reader import ImageReader
from ..errors import NotSupportedError


class BioformatsImageReader(ImageReader):

    '''
    Class for reading images using the
    `Bio-Formats <http://www.openmicroscopy.org/site/products/bio-formats>`_
    library.

    Raises
    ------
    NotSupportedError
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
            raise NotSupportedError('File format is not supported.')
        if except_value:
            sys.stdout.write('The following error occurred:\n%s'
                             % str(except_value))
            for tb in traceback.format_tb(except_trace):
                sys.stdout.write(tb)
