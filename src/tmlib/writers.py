import sys
import os
import h5py
import cv2
import numpy as np
import logging
import json
import yaml
import ruamel.yaml
import traceback
from abc import ABCMeta
from abc import abstractmethod
from gi.repository import Vips

logger = logging.getLogger(__name__)

'''
Writer Classes.


All writers make use of the 
`with statement context manager <https://docs.python.org/2/reference/datamodel.html#context-managers>`_.
and follow a similar syntax::

    with Writer('/path/to/folder') as writer:
        writer.write('name_of_file')

    with Writer() as writer:
        writer.write('/path/to/file')
'''


class Writer(object):
    '''
    Abstract writer base class.
    '''

    __metaclass__ = ABCMeta

    def __init__(self, directory=None):
        self.directory = directory

    def __enter__(self):
        return self

    def __exit__(self, except_type, except_value, except_trace):
        if except_value:
            sys.stdout.write('The following error occurred:\n%s'
                             % str(except_value))
            for tb in traceback.format_tb(except_trace):
                sys.stdout.write(tb)


class TextWriter(Writer):

    '''
    Abstract base class for writing text to files on disk.
    '''

    __metaclass__ = ABCMeta

    @abstractmethod
    def write(self, filename, data, **kwargs):
        pass


class XmlWriter(TextWriter):

    def __init__(self, directory=None):
        '''
        Initialize an object of class XmlWriter.

        Parameters
        ----------
        directory: str, optional
            absolute path to a directory where files are located
        '''
        super(XmlWriter, self).__init__(directory)
        self.directory = directory

    def write(self, filename, data, **kwargs):
        '''
        Parameters
        ----------
        filename: str
            name of the XML file
        data: list or dict
            the XML string that should be written to the file
        **kwargs: dict
            additional arguments as key-value pairs (none implemented)
        '''
        if self.directory:
            filename = os.path.join(self.directory, filename)
        logger.debug('write data to file: %s' % filename)
        with open(filename, 'w') as f:
            f.write(data)


class JsonWriter(TextWriter):

    def __init__(self, directory=None):
        '''
        Initialize an object of class JsonWriter.

        Parameters
        ----------
        directory: str, optional
            absolute path to a directory where files are located
        '''
        super(JsonWriter, self).__init__(directory)
        self.directory = directory

    def write(self, filename, data, **kwargs):
        '''
        Write data to JSON file.

        Parameters
        ----------
        filename: str
            name of the JSON file
        data: list or dict
            the JSON string that should be written to the file
        **kwargs: dict
            additional arguments as key-value pairs
            ("naicify": *bool*, whether `data` should be pretty-printed)

        Note
        ----
        `filename` will be truncated in case it already exists.
        '''
        if self.directory:
            filename = os.path.join(self.directory, filename)
        logger.debug('write data to file: %s' % filename)
        if 'naicify' in kwargs:
            naicify = kwargs['naicify']
        else:
            naicify = False
        with open(filename, 'w') as f:
            if naicify:
                json.dump(data, f, sort_keys=True,
                          indent=4, separators=(',', ': '))
            else:
                json.dump(data, f, sort_keys=True)


class YamlWriter(TextWriter):

    def __init__(self, directory=None):
        '''
        Initialize an object of class YamlWriter.

        Parameters
        ----------
        directory: str, optional
            absolute path to a directory where files are located
        '''
        super(YamlWriter, self).__init__(directory)
        self.directory = directory

    def write(self, filename, data, **kwargs):
        '''
        Write data to YAML file.

        Parameters
        ----------
        filename: str
            name of the YAML file
        data: list or dict
            the YAML string that should be written to the file
        **kwargs: dict
            additional arguments as key-value pairs
            ("use_ruamel": *bool*, when `ruamel.yaml` library should be used)


        Note
        ----
        `filename` will be truncated in case it already exists.
        '''
        if self.directory:
            filename = os.path.join(self.directory, filename)
        logger.debug('write data to file: %s' % filename)
        if 'use_ruamel' in kwargs:
            use_ruamel = kwargs['use_ruamel']
        else:
            use_ruamel = False
        with open(filename, 'w') as f:
            if use_ruamel:
                f.write(ruamel.yaml.dump(data,
                        Dumper=ruamel.yaml.RoundTripDumper,
                        explicit_start=True))
            else:
                f.write(yaml.safe_dump(data,
                        default_flow_style=False,
                        explicit_start=True))


class ImageWriter(Writer):

    def __init__(self, directory=None):
        '''
        Initialize an object of class ImageWriter.

        Parameters
        ----------
        directory: str, optional
            absolute path to a directory where files are located

        Raises
        ------
        OSError
            when directory does not exist
        '''
        super(ImageWriter, self).__init__(directory)
        self.directory = directory
        if not os.path.exists(self.directory):
            raise OSError('Directory does not exist: %s', self.directory)

    def write(self, filename, data, **kwargs):
        '''
        Write an image to file.

        The format depends on the file extension:
        - *.png for PNG (8-bit and 16-bit)
        - *.tiff or *.tif for TIFF (8-bit and 16-bit)
        - *.jpeg or *.jpg for JPEG (only supports 8-bit)

        Parameters
        ----------
        data: numpy.ndarray or Vips.Image 
            image that should be saved
        filename: str
            path to the image file
        **kwargs: dict
            additional arguments as key-value pairs (none implemented)

        Raises
        ------
        TypeError
            when `data` is not of type "numpy.ndarray" or "Vips.Image"
        '''
        if self.directory:
            filename = os.path.join(self.directory, filename)
        logger.debug('write image to file: %s' % filename)
        if isinstance(data, np.ndarray):
            if filename.endswith('.ppm'):
                cv2.imwrite(filename, data, [cv2.IMWRITE_PXM_BINARY, 0])
            else:
                cv2.imwrite(filename, data)
        elif isinstance(data, Vips.Image):
            data.write_to_file(filename)
        else:
            raise TypeError(
                    'Image must have type "numpy.ndarray" or "Vips.Image"')


class DatasetWriter(object):

    '''
    Base class for writing datasets and attributes to HDF5 files on disk.
    '''

    def __init__(self, filename, truncate=False):
        '''
        Initialize an instance of class DatasetWriter.

        Parameters
        ----------
        filename: str
            absolute path to HDF5 file
        truncate: bool, optional
            whether an existing file should be truncated, i.e. a new file
            created
        '''
        self.filename = filename
        self.truncate = truncate
        logger.debug('write data to file: %s', filename)

    def __enter__(self):
        if self.truncate:
            self._stream = h5py.File(self.filename, 'w')
        else:
            self._stream = h5py.File(self.filename, 'a')
        return self

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

    def write(self, path, data, index=None, row_index=None, column_index=None):
        '''
        Create a dataset.

        Parameters
        ----------
        path: str
            absolute path to the dataset within the file
        data:
            dataset; will be put through ``numpy.array(data)``
        index: int or List[int], optional
            zero-based index
        row_index: int or List[int], optional
            zero-based row index
        column_index: int or List[int], optional
            zero-based column index

        Returns
        -------
        h5py._hl.dataset.Dataset

        Raises
        ------
        TypeError
            when `data` has a different data type than an existing dataset
        IndexError
            when a provided index exceeds dimensions of an existing dataset
        KeyError
            when a subset of the dataset should be written, i.e. an index is
            provided, but the dataset does not yet exist
        IOError
            when `path` already exists

        Note
        ----
        If `data` is a nested list or array of arrays,
        a *variable_length* dataset with dimensions ``(len(data),)`` is
        created. For more information on *variable-length* types, see
        `h5py docs <http://docs.h5py.org/en/latest/special.html>`_.
        '''
        if isinstance(data, basestring):
            data = np.string_(data)
        if ((isinstance(data, np.ndarray) or isinstance(data, list)) and
                all([isinstance(d, basestring) for d in data])):
            data = [np.string_(d) for d in data]
        if isinstance(data, list):
            data = np.array(data)
        if index is None and row_index is None and column_index is None:
            if self.exists(path):
                raise IOError('Dataset already exists: %s', path)
            if isinstance(data, np.ndarray) and data.dtype == 'O':
                logger.debug('write dataset "%s" as variable length', path)
                dset = self._write_vlen(path, data)
            else:
                logger.debug('write dataset "%s"', path)
                dset = self._stream.create_dataset(path, data=data)
        else:
            if not self.exists(path):
                raise KeyError(
                        'In order to be able to write a subset of data, '
                        'the dataset has to exist: %s', path)
            dset = self._stream[path]

            if dset.dtype != data.dtype:
                raise TypeError(
                        'Data must have data type as dataset: '
                        'Dataset dtype: {0} - Data dtype: {1}'.format(
                            dset.dtype, data.dtype
                        ))

            if any(np.array(data.shape) > np.array(dset.shape)):
                raise IndexError(
                        'Data dimensions exceed dataset dimensions: '
                        'Dataset dims: {0} - Data dims: {1}'.format(
                            dset.shape, data.shape
                        ))
            if row_index is not None:
                if len(dset.shape) == 1:
                    raise IndexError(
                        'One-dimensional dataset does not allow '
                        'row-wise indexing: Dataset dims: {0}'.format(
                            dset.shape))
                if (len(list(row_index)) > data.shape[0] or
                        any(np.array(row_index) > dset.shape[0])):
                    raise IndexError(
                        'Row index exceeds dataset dimensions: '
                        'Dataset dims: {0}'.format(dset.shape))
            if column_index is not None:
                if len(dset.shape) == 1:
                    raise IndexError(
                        'One-dimensional dataset does not allow '
                        'column-wise indexing: Dataset dims: {0}'.format(
                            dset.shape))
                if (len(list(column_index)) > data.shape[1] or
                        any(np.array(column_index) > dset.shape[1])):
                    raise IndexError(
                        'Column index exceeds dataset dimension: '
                        'Dataset dims: {0}'.format(dset.shape))
            if index is not None:
                if len(dset.shape) > 1:
                    raise IndexError(
                        'Multi-dimensional dataset does not allow '
                        'element-wise indexing: Dataset dims: {0}'.format(
                            dset.shape))
                if (isinstance(index, list) and
                        isinstance(data, np.ndarray)):
                    if (len(index) > len(data) or
                            any(np.array(index) > len(dset))):
                        raise IndexError(
                            'Index exceeds dataset dimensions: '
                            'Dataset dims: {0}'.format(dset.shape))
                elif (isinstance(index, int) and
                        not isinstance(data, np.ndarray)):
                    if index > data:
                        raise IndexError(
                            'Index exceeds dataset dimensions: '
                            'Dataset dims: {0}'.format(dset.shape))
                else:
                    TypeError(
                        'Index must have have type int or list of int.')

            logger.debug('write data to a subset of dataset "%s"', path)
            if row_index and not column_index:
                dset[row_index, :] = data
            elif not row_index and column_index:
                dset[:, column_index] = data
            elif row_index and column_index:
                dset[row_index, column_index] = data
            elif index is not None:
                if (isinstance(index, list) and
                        isinstance(data, np.ndarray)):
                    for i, d in zip(index, data):
                        dset[i] = d.tolist()
                else:
                    dset[index] = data

        return dset

    def _write_vlen(self, path, data):
        data_type = np.unique([d.dtype for d in data])
        if len(data_type) == 0:
            dt = h5py.special_dtype(vlen=np.int64)
        else:
            dt = h5py.special_dtype(vlen=data_type[0])
        dset = self._stream.create_dataset(path, data.shape, dtype=dt)
        for i, d in enumerate(data):
            dset[i] = d.tolist()  # doesn't work with numpy.ndarray!!!
        return dset

    def preallocate(self, path, dims, dtype):
        '''
        Create a dataset with a given size and data type.

        Parameters
        ----------
        path: str
            absolute path to the dataset within the file
        dims: Tuple[int]
            dimensions of the dataset (number of rows and columns)
        dtype: type
            datatype the dataset

        Returns
        -------
        h5py._hl.dataset.Dataset

        Raises
        ------
        IOError
            when `path` already exists
        '''
        if self.exists(path):
            raise IOError('Dataset already exists: %s', path)
        return self._stream.create_dataset(path, dims, dtype)

    def set_attribute(self, path, name, data):
        '''
        Attach an attribute to a dataset.

        Parameters
        ----------
        path: str
            absolute path to the dataset within the file
        name: str
            name of the attribute
        data:
            value of the attribute; will be put through ``numpy.array(data)``
        '''
        if isinstance(data, basestring):
            data = np.string_(data)
        elif isinstance(data, list):
            data = [
                np.string_(d) if isinstance(d, basestring) else d
                for d in data
            ]
        self._stream[path].attrs.create(name, data)

    def __exit__(self, except_type, except_value, except_trace):
        self._stream.close()
