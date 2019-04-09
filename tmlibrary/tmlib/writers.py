# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016-2018 University of Zurich.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import sys
import os
import re
import h5py
import cv2
import numpy as np
import pandas as pd
import logging
import lxml.etree
import json
import yaml
import traceback
from abc import ABCMeta
from abc import abstractmethod

from tmlib.utils import same_docstring_as

logger = logging.getLogger(__name__)


class Writer(object):

    '''Abstract base class for writing data to files.

    Writers make use of the
    `with statement context manager <https://docs.python.org/2/reference/datamodel.html#context-managers>`_.
    and follow a similar syntax::

        with Writer('/path/to/file') as f:
            f.write()
    '''

    __metaclass__ = ABCMeta

    def __init__(self, filename):
        '''
        Parameters
        ----------
        filename: str
            absolute path to a file
        '''
        self.filename = filename

    def __enter__(self):
        self._stream = open(self.filename, 'w+')
        return self

    def __exit__(self, except_type, except_value, except_trace):
        self._stream.close()
        if except_value:
            sys.stdout.write(
                'The following error occurred while writing to file:\n%s'
                % str(except_value)
            )
            for tb in traceback.format_tb(except_trace):
                sys.stdout.write(tb)
            sys.exit(1)

    @abstractmethod
    def write(self, data):
        pass


class TextWriter(Writer):

    '''Class for writing text data to a file.'''

    @same_docstring_as(Writer.__init__)
    def __init__(self, filename):
        super(TextWriter, self).__init__(filename)

    def write(self, data):
        '''Writes data to file.

        Parameters
        ----------
        data: str
            text that should be written to the file
        '''
        logger.debug('write text data to file: %s' % self.filename)
        self._stream.write(data)


class XmlWriter(Writer):

    '''Class for writing data to a file in XML format.'''

    @same_docstring_as(Writer.__init__)
    def __init__(self, filename):
        super(XmlWriter, self).__init__(filename)

    def write(self, data):
        '''Writes data to XML file.

        Parameters
        ----------
        data: lxml.etree._Element
            xml element that should be written to the file
        '''
        logger.debug('write XML data to file: %s' % self.filename)
        self._stream.write(lxml.etree.tostring(data))


class JsonWriter(Writer):

    '''Class for writing data to file on disk in JSON format.'''

    @same_docstring_as(Writer.__init__)
    def __init__(self, filename):
        super(JsonWriter, self).__init__(filename)

    def write(self, data):
        '''Writes data to JSON file.

        Parameters
        ----------
        data: list or dict
            the JSON string that should be written to the file

        Note
        ----
        `filename` will be truncated in case it already exists.
        '''
        logger.debug('write JSON data to file: %s' % self.filename)
        json.dump(data, self._stream, sort_keys=True)


class YamlWriter(Writer):

    '''Class for writing data to file on disk in YAML 1.2 format'''

    @same_docstring_as(Writer.__init__)
    def __init__(self, filename):
        super(YamlWriter, self).__init__(filename)

    def write(self, data):
        '''Writes data to YAML file.

        Parameters
        ----------
        data: list or dict
            the YAML string that should be written to the file

        Note
        ----
        `filename` will be truncated in case it already exists.
        '''
        logger.debug('write YAML data to file: %s' % self.filename)
        yaml.dump(data, self._stream, explicit_start=True)


class ImageWriter(Writer):

    '''Class for writing :class:`numpy.ndarray` objects to image files
    using the `OpenCV <http://docs.opencv.org>`_ library.
    '''

    @same_docstring_as(Writer.__init__)
    def __init__(self, filename):
        super(ImageWriter, self).__init__(filename)

    def write(self, data):
        '''Writes pixels array data to image file.

        The format depends on the file extension:
            - \*.png for PNG (8-bit and 16-bit)
            - \*.tiff or \*.tif for TIFF (8-bit and 16-bit)
            - \*.jpeg or \*.jpg for JPEG (only supports 8-bit)

        Parameters
        ----------
        data: numpy.ndarray
            2D pixels plane that should be saved

        Raises
        ------
        TypeError
            when `data` is not of type numpy.ndarray
        ValueError
            when `data` has more than 2 dimensions
        '''
        logger.debug('write image data to file: %s' % self.filename)
        if not isinstance(data, np.ndarray):
            raise TypeError('Data must have type numpy.ndarray.')
        if data.ndim > 2:
            raise ValueError('Only 2D arrays are supported.')
        binary = cv2.imencode(os.path.splitext(self.filename)[1], data)[1]
        self._stream.write(binary)


class DataTableWriter(Writer):

    '''Class for writing data to a HDF5 file using the
    `pytables <http://www.pytables.org/>`_ library.'''

    def __init__(self, filename, truncate=False):
        '''
        Parameters
        ----------
        filename: str
            absolute path to a file
        truncate: bool, optional
            truncate the file if it already exists (default: ``False``)
        '''
        super(DataTableWriter, self).__init__(filename)
        self.truncate = truncate

    def __enter__(self):
        logger.debug('open file: %s', self.filename)
        if self.truncate:
            self._stream = pd.HDFStore(self.filename, 'w')
        else:
            self._stream = pd.HDFStore(self.filename, 'a')
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

    def write(self, path, data):
        '''Write a data table.

        Parameters
        ----------
        path: str
            absolute path to the dataset within the file
        data: pandas.DataFrame
            data table
        '''
        self._stream.put(path, data, format='table', data_columns=True)

    def append(self, path, data):
        '''Append an existing data table.

        Parameters
        ----------
        path: str
            absolute path to the dataset within the file
        data: pandas.DataFrame
            data table
        '''
        self._stream.append(path, data, format='table', data_columns=True)


class DatasetWriter(Writer):

    '''Class for writing data to a HDF5 file using the
    `h5py <http://docs.h5py.org/en/latest/index.html>`_ library.
    '''

    def __init__(self, filename, truncate=False):
        '''
        Parameters
        ----------
        filename: str
            absolute path to the HDF5 file
        truncate: bool, optional
            truncate the file if it already exists (default: ``False``)
        '''
        super(DatasetWriter, self).__init__(filename)
        self.truncate = truncate

    def __enter__(self):
        logger.debug('open file: %s', self.filename)
        if self.truncate:
            self._stream = h5py.File(self.filename, 'w')
        else:
            self._stream = h5py.File(self.filename, 'a')
        return self

    def exists(self, path):
        '''Checks whether `path` exists within the file.

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

    def write(self, path, data, compression=False):
        '''Creates a dataset and writes data to it.

        Parameters
        ----------
        path: str
            absolute path to the dataset within the file
        data:
            dataset; will be put through ``numpy.array(data)``
        compression: bool, optional
            whether zip compression filter should be applied
            (default: ``False``)

        Raises
        ------
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
            if len(data) == 1 and isinstance(data[0], np.ndarray):
                # Work around inconsistent numpy behavior for vlen datasets:
                # A list containing multiple numpy arrays of different shapes
                # are converted to a one-dimensional nested array of arrays
                # with object type, but a list containing a single numpy array
                # or multiple numpy arrays with the same shape to a
                # multi-dimensional array.
                empty = np.empty((1,), dtype='O')
                empty[0] = data[0]
                data = empty
            else:
                data = np.array(data)

        if isinstance(data, np.ndarray) and data.dtype == 'O':
            logger.debug('write dataset "%s" as variable length', path)
            self._write_vlen(path, data)
        else:
            logger.debug('write dataset "%s"', path)
            if self.exists(path):
                logger.warning(
                    'dataset "%s" in file "%s" will be overwritten',
                    path, self.filename
                )
                try:
                    self._stream[path][...] = data
                except:
                    raise IOError(
                        'Dataset "%s" in file "%s" could not be overwritten.'
                        % (path, self.filename)
                    )
            else:
                if compression:
                    self._stream.create_dataset(
                        path, data=data, compression='gzip'
                    )
                else:
                    self._stream.create_dataset(path, data=data)

    def write_subset(self, path, data,
                     index=None, row_index=None, column_index=None):
        '''Writes data to a subset of an existing dataset.

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

        Raises
        ------
        TypeError
            when `data` has a different data type than an existing dataset
        IndexError
            when a provided index exceeds dimensions of an existing dataset
        KeyError
            when a subset of the dataset should be written, i.e. an index is
            provided, but the dataset does not yet exist

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
            if len(data) == 1 and isinstance(data[0], np.ndarray):
                # Work around inconsistent numpy behavior for vlen datasets:
                # A list containing multiple numpy arrays of different shapes
                # are converted to a one-dimensional nested array of arrays
                # with object type, but a list containing a single numpy array
                # or multiple numpy arrays with the same shape to a
                # multi-dimensional array.
                empty = np.empty((1,), dtype='O')
                empty[0] = data[0]
                data = empty
            else:
                data = np.array(data)

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

    @staticmethod
    def _is_dataset(element):
        if isinstance(element.id, h5py.h5d.DatasetID):
            return True
        else:
            return False

    def list_datasets(self, path='/', pattern='.*'):
        '''Lists datasets within a given group.

        Parameters
        ----------
        path: str, optional
            absolute path to a group in the file (default: ``"/"``)
        pattern: str, optional
            regular expression pattern to filter datasets (default: ``".*"``)

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
        r = re.compile(pattern)
        for name, value in group.iteritems():
            if self._is_dataset(value) and r.search(name):
                names.append(name)
        return names

    def list_groups(self, path, pattern='.*'):
        '''Lists groups within a given group.

        Parameters
        ----------
        path: str
            absolute path to a group in the file
        pattern: str, optional
            regular expression pattern to filter groups (default: ``".*"``)

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
        r = re.compile(pattern)
        for name, value in group.iteritems():
            if not self._is_dataset(value) and r.search(name):
                names.append(name)
        return names

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

    def create(self, path, dims, dtype, max_dims=None):
        '''Creates a dataset with a given size and data type without actually
        writing data to it.

        Parameters
        ----------
        path: str
            absolute path to the dataset within the file
        dims: Tuple[int]
            dimensions of the dataset (number of rows and columns)
        dtype: type
            datatype the dataset
        max_dims: Tuple[int]
            maximal dimensions of the dataset, useful if the dataset should
            be extendable along one or more dimensions (defaults to `dims`);
            ``(None, None)`` would mean extendable infinitely along both
            dimensions

        Returns
        -------
        h5py._hl.dataset.Dataset

        Raises
        ------
        IOError
            when `path` already exists
        '''
        if max_dims is None:
            max_dims = dims
        if self.exists(path):
            raise IOError('Dataset already exists: %s' % path)
        return self._stream.create_dataset(
                        path, shape=dims, dtype=dtype, maxshape=max_dims)

    def append(self, path, data):
        '''Appends data to an existing one-dimensional dataset.
        The dataset needs to be created first using the
        :func:`tmlib.writers.DatasetWriter.create` method and the
        `max_dims` entry for the vertical dimension needs to be
        set to ``None``.

        Parameters
        ----------
        path: str
            absolute path to the dataset within the file
        data:
            dataset; will be put through ``numpy.array(data)``

        Raises
        ------
        ValueError
            when the dataset is one-dimensional or when vertical dimensions of
            `data` and the dataset don't match
        TypeError
            when data types of `data` and the dataset don't match

        Note
        ----
        Creates the dataset in case it doesn't yet exist.
        '''
        data = np.array(data)
        if not self.exists(path):
            logger.debug('create dataset "%s"', path)
            # preallocate an empty dataset that can be extended
            self.create(
                    path, dims=(0, ), dtype=data.dtype,
                    max_dims=(None, ))
        dset = self._stream[path]
        if len(dset.shape) > 1:
            raise ValueError('Data must be one-dimensional: %s', path)
        if len(data.shape) > 1:
            raise ValueError('Data dimensions do not match.')
        if dset.dtype != data.dtype:
            raise TypeError('Data types don\'t  match.')
        start_index = len(dset)
        end_index = start_index + len(data)
        dset.resize((len(dset) + len(data), ))
        self.write(path, data, index=range(start_index, end_index))
        # dset[start_index:] = data

    def vstack(self, path, data):
        '''Vertically appends data to an existing multi-dimensional dataset.
        The dataset needs to be created first using the
        :func:`tmlib.writers.DatasetWriter.create` method and the
        `max_dims` entry for the vertical dimension needs to be
        set to ``None``.

        Parameters
        ----------
        path: str
            absolute path to the dataset within the file
        data:
            dataset; will be put through ``numpy.array(data)``

        Raises
        ------
        ValueError
            when the dataset is one-dimensional or when vertical dimensions of
            `data` and the dataset don't match
        TypeError
            when data types of `data` and the dataset don't match

        Note
        ----
        Creates the dataset in case it doesn't yet exist.
        If `data` is one-dimensional a dataset with dimensions
        ``(0, len(data))`` will be created.
        '''
        data = np.array(data)
        if not self.exists(path):
            logger.debug('create dataset "%s"', path)
            # preallocate an empty dataset that can be extended along the
            # vertical axis
            if len(data.shape) > 1:
                self.create(
                        path, dims=(0, data.shape[1]), dtype=data.dtype,
                        max_dims=(None, data.shape[1]))
            else:
                self.create(
                        path, dims=(0, len(data)), dtype=data.dtype,
                        max_dims=(None, len(data)))
        dset = self._stream[path]
        if not len(dset.shape) > 1:
            raise ValueError('Data must be multi-dimensional: %s', path)
        if len(data.shape) > 1:
            if data.shape[1] != dset.shape[1]:
                raise ValueError('Dataset dimensions do not match.')
            add = data.shape[0]
        else:
            if len(data) != dset.shape[1]:
                raise ValueError('Dataset dimensions do not match.')
            add = 1
        if dset.dtype != data.dtype:
            raise TypeError('Data types don\'t  match.')
        start_index = dset.shape[0]
        dset.resize((dset.shape[0] + add, dset.shape[1]))
        dset[start_index:, :] = data

    def hstack(self, path, data):
        '''Horizontally appends data to an existing multi-dimensional dataset.
        The dataset needs to be created first using the
        :func:`tmlib.writers.DatasetWriter.create` method and the
        `max_dims` entry for the horizontal dimension needs to be
        set to ``None``.

        Parameters
        ----------
        path: str
            absolute path to the dataset within the file
        data:
            dataset; will be put through ``numpy.array(data)``

        Raises
        ------
        IOError
            when `path` doesn't exist
        ValueError
            when the dataset is one-dimensional or when horizontal dimensions
            of `data` and the dataset don't match
        TypeError
            when data types of `data` and the dataset don't match

        Note
        ----
        Creates the dataset in case it doesn't yet exist.
        If `data` is one-dimensional a dataset with dimensions
        ``(len(data), 0)`` will be created.
        '''
        data = np.array(data)
        if not self.exists(path):
            logger.debug('create dataset "%s"', path)
            # preallocate an empty dataset that can be extended along the
            # horizontal axis
            if len(data.shape) > 1:
                self.create(
                        path, dims=(data.shape[0], 0), dtype=data.dtype,
                        max_dims=(data.shape[0], None))
            else:
                self.create(
                        path, dims=(len(data), 0), dtype=data.dtype,
                        max_dims=(len(data), None))
        dset = self._stream[path]
        if not len(dset.shape) > 1:
            raise ValueError('Data must be multi-dimensional: %s', path)
        if len(data.shape) > 1:
            if data.shape[0] != dset.shape[0]:
                raise ValueError('Dataset dimensions don\'t match.')
            add = data.shape[1]
        else:
            if len(data) != dset.shape[0]:
                raise ValueError('Dataset dimensions don\'t match.')
            add = 1
        if dset.dtype != data.dtype:
            raise TypeError('Data types don\'t match.')
        start_index = dset.shape[1]
        dset.resize((dset.shape[0], dset.shape[1] + add))
        dset[:, start_index:] = data

    def set_attribute(self, path, name, data):
        '''Attachs an attribute to a dataset.

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

    def create_group(self, path):
        '''Creates a group.

        Parameters
        ----------
        path: str
            absolute path to the group within the file
        '''
        if not self.exists(path):
            self._stream.create_group(path)
