import os
import sys
import h5py
import logging
import json
import ruamel.yaml
import traceback
import lxml.etree
import cv2
import bioformats
import javabridge
import numpy as np
import pandas as pd
from abc import ABCMeta
from abc import abstractmethod

from tmlib.errors import NotSupportedError
from tmlib.utils import same_docstring_as

logger = logging.getLogger(__name__)


class Reader(object):

    '''Abstract base class for reading data from files.

    Readers make use of the 
    `with statement context manager <https://docs.python.org/2/reference/datamodel.html#context-managers>`_.
    and thus follow a similar syntax::

        with Reader('/path/to/file') as f:
            data = f.read()
    '''

    __metaclass__ = ABCMeta

    def __init__(self, filename):
        '''
        Parameters
        ----------
        filename: str
            absolute path to a file

        Raises
        ------
        OSError
            when `filename` does not exist
        '''
        if not os.path.exists(filename):
            raise OSError('File does not exist: %s' % filename)
        self.filename = filename

    def __enter__(self):
        logger.debug('open file: %s', self.filename)
        self._stream = open(self.filename, 'r')
        return self

    def __exit__(self, except_type, except_value, except_trace):
        logger.debug('close file: %s', self.filename)
        self._stream.close()
        if except_value:
            sys.stdout.write(
                'The following error occurred while reading from file:\n%s'
                % str(except_value)
            )
            for tb in traceback.format_tb(except_trace):
                sys.stdout.write(tb)
            sys.exit(1)

    @abstractmethod
    def read(self):
        pass


class TextReader(Reader):

    '''Class for reading data from text files.'''

    @same_docstring_as(Reader.__init__)
    def __init__(self, filename):
        super(TextReader, self).__init__(filename)

    def read(self):
        '''Read data from text file.

        Returns
        -------
        lxml.etree._Element
            xml
        '''
        logger.debug('read from file: %s', self.filename)
        return self._stream.read()


class XmlReader(Reader):

    # TODO: implement xpath subset reading via lxml
    '''Class for reading data from files in XML format.'''

    @same_docstring_as(Reader.__init__)
    def __init__(self, filename):
        super(XmlReader, self).__init__(filename)

    def read(self):
        '''Read data from XML file.

        Returns
        -------
        lxml.etree._Element
            xml
        '''
        logger.debug('read from file: %s', self.filename)
        return lxml.etree.fromstring(self._stream.read())


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


class JsonReader(Reader):

    '''Class for reading data from files in JSON format.'''

    @same_docstring_as(Reader.__init__)
    def __init__(self, filename):
        super(JsonReader, self).__init__(filename)

    def read(self):
        '''Read data from JSON file.

        Returns
        -------
        dict or list
            file content
        '''
        logger.debug('read from file: %s', self.filename)
        return load_json(self._stream.read())


def load_yaml(string):
    '''Convert YAML string to Python object.

    Parameters
    ----------
    string: str
        YAML string

    Returns
    -------
    dict or list
    '''
    return ruamel.yaml.load(string, ruamel.yaml.RoundTripLoader)


class YamlReader(Reader):

    '''Class for reading data from files in YAML 1.2 format.'''

    @same_docstring_as(Reader.__init__)
    def __init__(self, filename):
        super(YamlReader, self).__init__(filename)

    def read(self):
        '''Read YAML file.

        Returns
        -------
        dict or list
            file content
        '''
        logger.debug('read from file: %s', self.filename)
        return load_yaml(self._stream.read())


class TablesReader(Reader):

    '''Class for reading datasets and attributes from HDF5 files
    using the `pytables <http://www.pytables.org/>`_ library.
    '''

    @same_docstring_as(Reader.__init__)
    def __init__(self, filename):
        super(TablesReader, self).__init__(filename)

    def __enter__(self):
        logger.debug('open file: %s', self.filename)
        self._stream = pd.HDFStore(self.filename, 'r')
        return self

    def exists(self, path):
        '''Check whether a `path` exists within the file.

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
        '''Read a dataset.

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


class DatasetReader(Reader):

    '''Class for reading datasets and attributes from HDF5 files
    using the `h5py <http://docs.h5py.org/en/latest/>`_ library.
    '''

    @same_docstring_as(Reader.__init__)
    def __init__(self, filename):
        super(DatasetReader, self).__init__(filename)

    def __enter__(self):
        logger.debug('open file: %s', self.filename)
        # NOTE: The file shouldn't be opened in read-only mode, because this
        # would prevent concomitant writing
        self._stream = h5py.File(self.filename, 'r+')
        return self

    def exists(self, path):
        '''Check whether a `path` exists within the file.

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
        '''List datasets within a given group.

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
        '''List groups within a given group.

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
        '''Read a dataset.

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
        '''Read a subset of a dataset. For *fancy-indexing* see
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
        '''Get an attribute attached to a dataset.

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
        '''Get the dimensions of a dataset.

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
        ''''Get the data type of a dataset.

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


class BFImageReader(object):

    '''Class for reading data from vendor-specific image file formats as
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
    >>> with BFImageReader() as reader:
    ...     img = reader.read(filename)
    >>> type(img)
    numpy.ndarray
    '''

    @same_docstring_as(Reader.__init__)
    def __init__(self, directory=None):
        self.directory = directory

    def __enter__(self):
        # NOTE: updated "loci_tools.jar" file to latest schema:
        # http://downloads.openmicroscopy.org/bio-formats/5.1.3
        javabridge.start_vm(class_path=bioformats.JARS, run_headless=True)
        return self

    def __exit__(self, except_type, except_value, except_trace):
        javabridge.kill_vm()
        if except_type is javabridge.JavaException:
            raise NotSupportedError('File format is not supported.')
        if except_value:
            sys.stdout.write('The following error occurred:\n%s'
                             % str(except_value))
            for tb in traceback.format_tb(except_trace):
                sys.stdout.write(tb)

    def read(self, filename):
        '''Read an image from a file.

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
        '''Read a subset of images from a file.

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


class PixelsReader(Reader):

    '''Class for reading pixel data from standard image file formats as
    :py:class:`numpy.ndarray` objects.
    '''

    @same_docstring_as(Reader.__init__)
    def __init__(self, filename):
        super(PixelsReader, self).__init__(filename)

    def read(self, dtype=np.uint16):
        '''Read pixels data from image file.

        Parameters
        ----------
        dtype: type, optional
            `numpy` data type (default: ``numpy.uint16``)

        Returns
        -------
        numpy.ndarray
            pixels data
        '''
        logger.debug('read from file: %s', self.filename)
        arr = np.fromstring(self._stream.read(), dtype)
        return cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
        # return cv2.imread(filename, cv2.IMREAD_UNCHANGED)
