import sys
import traceback
import h5py
from abc import ABCMeta
from abc import abstractmethod


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
    def read_subset(self, filename, series=None, plane=None):
        pass

    def __exit__(self, except_type, except_value, except_trace):
        pass


class SlideReader(object):

    '''
    Abstract base class for reading whole slide images from files on disk.
    '''

    __metaclass__ = ABCMeta

    def __enter__(self):
        return self

    @abstractmethod
    def read(self, filename):
        pass

    @abstractmethod
    def split(self):
        pass

    def __exit__(self, except_type, except_value, except_trace):
        pass


class DatasetReader(object):

    '''
    Base class for reading datasets and attributes from HDF5 files on disk.
    '''

    def __init__(self, filename):
        self.filename = filename

    def __enter__(self):
        self._stream = h5py.File(self.filename, 'r')
        return self

    # TODO: raise Exception if dataset does not exist

    def exists(self, path):
        '''
        Check whether a `path` exists within a file.

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
        if isinstance(element.id, h5py.h5g.GroupID):
            return True
        else:
            return True

    def list_dataset_names(self, path):
        '''
        Parameters
        ----------
        path: str
            absolute path to a group in the file

        Returns
        -------
        List[str]
            names of the datasets in `path`
        '''
        names = list()
        for name, value in self._stream[path].iteritems():
            if self._is_dataset(value):
                names.append(name)

        return names

    def list_group_names(self, path):
        '''
        Parameters
        ----------
        path: str
            absolute path to a group in the file

        Returns
        -------
        List[str]
            names of the groups in `path`
        '''
        names = list()
        for name, value in self._stream[path].iteritems():
            if self._is_group(value):
                names.append(name)

        return names

    def read(self, path, index=None, row_index=None, column_index=None):
        '''
        Read a dataset. For *fancy-indexing* see
        `h5py docs <http://docs.h5py.org/en/latest/high/dataset.html#fancy-indexing>`_.

        Parameters
        ----------
        path: str
            absolute path to the dataset within the file
        index: int or List[int], option
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
            when `path` doesn't point to an existing dataset
        '''
        try:
            dataset = self._stream[path]
        except KeyError:
            raise KeyError('Dataset does not exist: %s' % path)
        if row_index and not column_index:
            if len(dataset.shape) == 1:
                raise IndexError(
                    'Dataset dimensions do not allow row-wise indexing')
            return dataset[row_index, :]
        elif not row_index and column_index:
            if len(dataset.shape) == 1:
                raise IndexError(
                    'Dataset dimensions do not allow column-wise indexing')
            return dataset[:, column_index]
        elif row_index and column_index:
            if len(dataset.shape) == 1:
                raise IndexError(
                    'Dataset dimensions do not allow row/column-wise indexing')
            return dataset[row_index, column_index]
        elif index:
            return dataset[index]
        else:
            return dataset[()]

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
            when `path` doesn't point to an existing dataset
        AttributeError
            when dataset does not have an attribute called `name`
        '''
        try:
            dataset = self._stream[path]
        except KeyError:
            raise KeyError('Dataset does not exist: %s' % path)
        attribute = dataset.attrs.get(name)
        if not attribute:
            raise AttributeError(
                    'Dataset does not have an attribute "%s": %s' % path)
        return attribute

    def __exit__(self, except_type, except_value, except_trace):
        self._stream.close()


class MetadataReader(object):

    '''
    Abstract base class for reading metadata from additional (non-image) files.

    They return metadata as OMEXML objects, according to the OME data model,
    see `python-bioformats <http://pythonhosted.org/python-bioformats/#metadata>`_.

    Unfortunately, the documentation is very sparse.
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

    def __enter__(self):
        return self

    @abstractmethod
    def read(self, filename):
        pass

    def __exit__(self, except_type, except_value, except_trace):
        if except_value:
            sys.stdout.write('The following error occurred:\n%s'
                             % str(except_value))
            for tb in traceback.format_tb(except_trace):
                sys.stdout.write(tb)
