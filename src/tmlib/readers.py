import os
import sys
import h5py
import logging
import json
import yaml
import ruamel.yaml
import traceback
import cv2
import bioformats
import javabridge
import pandas as pd
from gi.repository import Vips
from abc import ABCMeta
from abc import abstractmethod
from .errors import NotSupportedError
from . import utils

logger = logging.getLogger(__name__)


class Reader(object):

    '''
    Abstract base class for reading data from files.

    All readers make use of the 
    `with statement context manager <https://docs.python.org/2/reference/datamodel.html#context-managers>`_.
    and follow a similar syntax::

        with Reader('/path/to/folder') as reader:
            data = reader.read('name_of_file')

        with Reader() as reader:
            data = reader.read('/path/to/file')
    '''

    __metaclass__ = ABCMeta

    def __init__(self, directory=None):
        '''
        Parameters
        ----------
        directory: str, optional
            absolute path to a directory where files are located

        Raises
        ------
        OSError
            when `directory` does not exist
        '''
        self.directory = directory
        if self.directory is not None:
            if not os.path.exists(self.directory):
                raise OSError('Directory does not exist: %s', self.directory)

    def __enter__(self):
        return self

    def __exit__(self, except_type, except_value, except_trace):
        pass
        # if except_value:
        #     sys.stdout.write('%s\n' % str(except_value))
        #     for tb in traceback.format_tb(except_trace):
        #         sys.stdout.write(tb)


class TextReader(Reader):
    '''
    Abstract base class for reading text from files.
    '''

    __metaclass__ = ABCMeta

    @abstractmethod
    def read(self, filename, **kwargs):
        pass


class XmlReader(TextReader):

    # TODO: implement xpath subset reading via lxml
    '''
    Class for reading data from files in XML format.
    '''

    @utils.same_docstring_as(Reader.__init__)
    def __init__(self, directory=None):
        super(XmlReader, self).__init__(directory)

    def read(self, filename):
        '''
        Read data from XML file.

        Parameters
        ----------
        filename: str
            path to the file

        Returns
        -------
        basestring
            xml string

        Raises
        ------
        OSError
            when `filename` does not exist
        '''
        if self.directory:
            filename = os.path.join(self.directory, filename)
        if not os.path.exists(filename):
            raise OSError('File does not exist: %s' % filename)
        with open(filename, 'r') as f:
            return f.read()


def load_json(string):
    '''
    Convert JSON string to Python object.

    Parameters
    ----------
    string: str
        JSON string

    Returns
    -------
    dict or list
    '''
    return json.loads(string)


class JsonReader(TextReader):
    '''
    Class for reading data from files in JSON format.
    '''

    @utils.same_docstring_as(Reader.__init__)
    def __init__(self, directory=None):
        super(JsonReader, self).__init__(directory)

    def read(self, filename, **kwargs):
        '''
        Read data from JSON file.

        Parameters
        ----------
        filename: str
            path to the file

        Returns
        -------
        dict or list
            file content

        Raises
        ------
        OSError
            when `filename` does not exist
        '''
        if self.directory:
            filename = os.path.join(self.directory, filename)
        if not os.path.exists(filename):
            raise OSError('File does not exist: %s' % filename)
        logger.debug('read file: %s', filename)
        with open(filename, 'r') as f:
            return load_json(f.read())


def load_yaml(string):
    '''
    Convert YAML string to Python object.

    Parameters
    ----------
    string: str
        YAML string

    Returns
    -------
    dict or list
    '''
    return ruamel.yaml.load(string, ruamel.yaml.RoundTripLoader)


class YamlReader(TextReader):
    '''
    Class for reading data from files in YAML 1.2 format.
    '''

    @utils.same_docstring_as(Reader.__init__)
    def __init__(self, directory=None):

        super(YamlReader, self).__init__(directory)

    def read(self, filename):
        '''
        Read YAML file.

        Parameters
        ----------
        filename: str
            path to the YAML file

        Returns
        -------
        dict or list
            file content

        Raises
        ------
        OSError
            when `filename` does not exist
        '''
        if self.directory:
            filename = os.path.join(self.directory, filename)
        if not os.path.exists(filename):
            raise OSError('File does not exist: %s' % filename)
        logger.debug('read file: %s', filename)
        with open(filename, 'r') as f:
            return load_yaml(f.read())


class TablesReader(object):

    '''
    Class for reading datasets and attributes from HDF5 files
    using the `pytables <http://www.pytables.org/>`_ library.
    '''

    def __init__(self, filename):
        '''
        Parameters
        ----------
        filename: str
            absolute path to HDF5 file
        '''
        self.filename = filename

    def __enter__(self):
        logger.debug('open file: %s', self.filename)
        self._stream = pd.HDFStore(self.filename, 'r')
        return self

    def __exit__(self, except_type, except_value, except_trace):
        logger.debug('close file: %s', self.filename)
        self._stream.close()
        if except_value:
            sys.stdout.write('The following error occurred:\n%s'
                             % str(except_value))
            for tb in traceback.format_tb(except_trace):
                sys.stdout.write(tb)

    def exists(self, path):
        '''
        Check whether a `path` exists within the file.

        Parameters
        ----------
        path: str
            absolute path to a group or dataset in the file

        Returns
        -------
        bool
            ``True`` if `path` exists and ``False`` otherwise
        '''
        if path in self._stream:
            return True
        else:
            return False

    def read(self, path):
        '''
        Read a dataset.

        Parameters
        ----------
        path: str
            absolute path to the dataset within the file

        Returns
        -------
        pandas.DataFrame
            dataset

        Raises
        ------
        IOError
            when `path` already exists
        '''
        return self._stream.select(path)


class DatasetReader(object):

    '''
    Class for reading datasets and attributes from HDF5 files
    using the `h5py <http://docs.h5py.org/en/latest/>`_ library.
    '''

    def __init__(self, filename):
        '''
        Parameters
        ----------
        filename: str
            absolute path to HDF5 file
        '''
        self.filename = filename

    def __enter__(self):
        logger.debug('open file: %s', self.filename)
        # NOTE: The file shouldn't be opened in read-only mode, because this
        # would prevent concomitant writing
        self._stream = h5py.File(self.filename, 'r+')
        return self

    def __exit__(self, except_type, except_value, except_trace):
        logger.debug('close file: %s', self.filename)
        self._stream.close()
        if except_value:
            sys.stdout.write('The following error occurred:\n%s'
                             % str(except_value))
            for tb in traceback.format_tb(except_trace):
                sys.stdout.write(tb)

    def exists(self, path):
        '''
        Check whether a `path` exists within the file.

        Parameters
        ----------
        path: str
            absolute path to a group or dataset in the file

        Returns
        -------
        bool
            ``True`` if `path` exists and ``False`` otherwise
        '''
        if path in self._stream:
            return True
        else:
            return False

    @staticmethod
    def _is_dataset(element):
        if isinstance(element.id, h5py.h5d.DatasetID):
            return True
        else:
            return False

    @staticmethod
    def _is_group(element):
        # TODO: this doesn't work, also lists datasets
        if isinstance(element.id, h5py.h5g.GroupID):
            return True
        else:
            return True

    def list_datasets(self, path):
        '''
        Parameters
        ----------
        path: str
            absolute path to a group in the file

        Returns
        -------
        List[str]
            names of the datasets in `path`

        Raises
        ------
        KeyError
            when `path` does not exist
        '''
        try:
            group = self._stream[path]
        except KeyError:
            raise KeyError('Group does not exist: %s' % path)
        names = list()
        for name, value in group.iteritems():
            if self._is_dataset(value):
                names.append(name)

        return names

    def list_groups(self, path):
        '''
        Parameters
        ----------
        path: str
            absolute path to a group in the file

        Returns
        -------
        List[str]
            names of the groups in `path`

        Raises
        ------
        KeyError
            when `path` does not exist
        '''
        try:
            group = self._stream[path]
        except KeyError:
            raise KeyError('Group does not exist: %s' % path)
        names = list()
        for name, value in group.iteritems():
            if not self._is_dataset(value):
                names.append(name)

        return names

    def read(self, path):
        '''
        Read a dataset.

        Parameters
        ----------
        path: str
            absolute path to the dataset within the file

        Returns
        -------
        numpy.ndarray
            dataset

        Raises
        ------
        KeyError
            when `path` does not exist
        '''
        try:
            dset = self._stream[path]
        except KeyError:
            raise KeyError('Dataset does not exist: %s' % path)
        return dset[()]

    def read_subset(self, path, index=None, row_index=None, column_index=None):
        '''
        Read a subset of a dataset. For *fancy-indexing* see
        `h5py docs <http://docs.h5py.org/en/latest/high/dataset.html#fancy-indexing>`_.

        Parameters
        ----------
        path: str
            absolute path to the dataset within the file
        index: int or List[int], optional
            zero-based index
        row_index: int or List[int], optional
            zero-based row index
        column_index: int or List[int], optional
            zero-based column index

        Returns
        -------
        numpy.ndarray
            dataset

        Raises
        ------
        KeyError
            when `path` does not exist
        '''
        try:
            dset = self._stream[path]
        except KeyError:
            raise KeyError('Dataset does not exist: %s' % path)
        if row_index and not column_index:
            if len(dset.shape) == 1:
                raise IndexError(
                    'Dataset dimensions do not allow row-wise indexing')
            return dset[row_index, :]
        elif not row_index and column_index:
            if len(dset.shape) == 1:
                raise IndexError(
                    'Dataset dimensions do not allow column-wise indexing')
            return dset[:, column_index]
        elif row_index and column_index:
            if len(dset.shape) == 1:
                raise IndexError(
                    'Dataset dimensions do not allow row/column-wise indexing')
            return dset[row_index, column_index]
        elif index is not None:
            return dset[index]
        else:
            raise ValueError('No index provided.')

    def get_attribute(self, path, name):
        '''
        Get an attribute attached to a dataset.

        Parameters
        ----------
        path: str
            absolute path to the dataset within the file
        name: str
            name of the attribute

        Returns
        -------
        ???

        Raises
        ------
        KeyError
            when `path` does not exist
        AttributeError
            when dataset does not have an attribute called `name`
        '''
        try:
            dset = self._stream[path]
        except KeyError:
            raise KeyError('Dataset does not exist: %s' % path)
        attribute = dset.attrs.get(name)
        if not attribute:
            raise AttributeError(
                    'Dataset doesn\'t have an attribute "%s": %s'
                    % (name, path))
        return attribute

    def get_dims(self, path):
        '''
        Get the dimensions of a dataset.

        Parameters
        ----------
        path: str
            absolute path to the dataset within the file

        Returns
        -------
        Tuple[int]
            number of rows and columns of the dataset

        Raises
        ------
        KeyError
            when `path` does not exist
        '''
        try:
            dims = self._stream[path].shape
        except KeyError:
            raise KeyError('Dataset does not exist: %s' % path)
        return dims

    def get_type(self, path):
        ''''
        Get the data type of a dataset.

        Parameters
        ----------
        path: str
            absolute path to the dataset within the file

        Returns
        -------
        type
            data type of the dataset

        Raises
        ------
        KeyError
            when `path` does not exist
        '''
        try:
            dtype = self._stream[path].dtype
        except KeyError:
            raise KeyError('Dataset does not exist: %s' % path)
        return dtype


class ImageReader(Reader):

    '''
    Class for reading data from vendor-specific image file formats as
    :py:class:`numpy.ndarray` objects using the
    `Bio-Formats <http://www.openmicroscopy.org/site/products/bio-formats>`_
    library.

    Note
    ----
    Requires a running Java Virtual Machine (VM). This is handled automatically
    via `javabridge <http://pythonhosted.org/javabridge/start_kill.html>`_.

    Warning
    -------
    Once the VM is killed it cannot be started again within the same Python
    session.

    Examples
    --------
    >>> filename = '/path/to/image/file'
    >>> with ImageReader() as reader:
    ...     img = reader.read(filename)
    >>> type(img)
    numpy.ndarray
    '''

    @utils.same_docstring_as(Reader.__init__)
    def __init__(self, directory=None):
        super(ImageReader, self).__init__(directory)

    def __enter__(self):
        # NOTE: updated "loci_tools.jar" file to latest schema:
        # http://downloads.openmicroscopy.org/bio-formats/5.1.3
        javabridge.start_vm(class_path=bioformats.JARS, run_headless=True)
        return self

    def read(self, filename):
        '''
        Read an image from a file.

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
        if self.directory:
            filename = os.path.join(self.directory, filename)
        if not os.path.exists(filename):
            raise OSError('Image file does not exist: %s' % filename)
        logger.debug('read image pixels from file: %s', filename)
        image = bioformats.load_image(filename, rescale=False)
        return image

    def read_subset(self, filename, series=None, plane=None):
        '''
        Read a subset of images from a file.

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
        if self.directory:
            filename = os.path.join(self.directory, filename)
        logger.debug('read data from file: %s' % filename)
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


class NumpyReader(Reader):

    '''
    Class for reading data from standard image file formats as
    :py:class:`numpy.ndarray` objects.

    Examples
    --------
    >>> filename = '/path/to/image/file'
    >>> with NumpyReader() as reader:
    ...     img = reader.read(filename)
    >>> type(img)
    numpy.ndarray
    '''

    @utils.same_docstring_as(Reader.__init__)
    def __init__(self, directory=None):
        super(NumpyReader, self).__init__(directory)

    def read(self, filename):
        '''
        Read an image from file.

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
        if self.directory:
            filename = os.path.join(self.directory, filename)
        if not os.path.exists(filename):
            raise OSError('Image file does not exist: %s' % filename)
        logger.debug('read image from file: %s', filename)
        image = cv2.imread(filename, cv2.IMREAD_UNCHANGED)
        return image

    def read_subset(self, filename, series=None, plane=None):
        '''
        If the image file contains more than one plane (band), only the first
        one will be read.
        '''
        raise AttributeError('%s doesn\'t have a "read_subset" method'
                             % self.__class__.__name__)


class VipsReader(Reader):

    '''
    Class for reading data from files as :py:class:`Vips.Image` objects.

    Uses the
    `Vips <http://www.vips.ecs.soton.ac.uk/index.php?title=Libvips>`_ library.

    Examples
    --------
    >>> filename = '/path/to/image/file'
    >>> with VipsReader() as reader:
    ...     img = reader.read(filename)
    >>> type(img)
    Vips.Image
    '''

    @utils.same_docstring_as(Reader.__init__)
    def __init__(self, directory=None):
        super(VipsReader, self).__init__(directory)

    def read(self, filename):
        '''
        Read an image from file.

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

        Note
        ----
        Images are read with access mode `Vips.Access.SEQUENTIAL_UNBUFFERED`
        to save memory. For more information, please refer to the
        `Vips documentation <http://www.vips.ecs.soton.ac.uk/supported/current/doc/html/libvips/libvips-VipsImage.html#VIPS-ACCESS-SEQUENTIAL-UNBUFFERED:CAPS>`_
        
        See also
        --------
        :py:meth:`Vips.Image.new_from_file()`
        '''
        if self.directory:
            filename = os.path.join(self.directory, filename)
        if not os.path.exists(filename):
            raise OSError('Image file does not exist: %s' % filename)
        image = Vips.Image.new_from_file(
                    filename, access=Vips.Access.SEQUENTIAL_UNBUFFERED)
        return image


class SlideReader(object):

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
        return Vips.Image.openslideload(filename, level=0)

    def read_subset(self, filename, series_index=None, plane_index=None):
        raise AttributeError('%s doesn\'t have a "read_subset" method. '
                             'If the file contains more than one plane/band, '
                             'only the first one will be read.'
                             % self.__class__.__name__)


class MetadataReader(Reader):

    '''
    Abstract base class for reading metadata from additional (non-image) files.

    They return metadata as OMEXML objects, according to the OME data model,
    see `python-bioformats <http://pythonhosted.org/python-bioformats/#metadata>`_.

    Unfortunately, the documentation is very sparse.squ 
    If you need additional information, refer to the relevant
    `source code <https://github.com/CellProfiler/python-bioformats/blob/master/bioformats/omexml.py>`_.

    Note
    ----
    In case custom readers provide a *Plate* element, they also have to specify
    an *ImageRef* elements for each *WellSample* element, which serve as
    references to OME *Image* elements. Each *ImageRef* attribute must be a
    dictionary with a single entry. The value must be a list of strings, where
    each element represents the reference information that can be used to map
    the *WellSample* element to an individual *Image* element. The key must be
    a regular expression string that can be used to extract the reference
    information from the corresponding image filenames.
    '''

    __metaclass__ = ABCMeta

    @utils.same_docstring_as(Reader.__init__)
    def __init__(self, directory=None):
        super(MetadataReader, self).__init__(directory)

    @abstractmethod
    def read(self, filename):
        pass
