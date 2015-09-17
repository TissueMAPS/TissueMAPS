import h5py
import numpy as np


class DatasetWriter(object):

    '''
    Base class for writing datasets and attributes to HDF5 files on disk.
    '''

    def __init__(self, filename):
        self.filename = filename

    def __enter__(self):
        self._stream = h5py.File(self.filename, 'a')
        return self

    def write_dataset(self, path, data):
        '''
        Create a dataset.

        Parameters
        ----------
        path: str
            absolute path to the dataset within the file
        data:
            dataset; will be put through ``numpy.array(data)``

        Returns
        -------
        numpy.ndarray
            dataset
        '''
        if isinstance(data, basestring):
            data = np.string_(data)
        self._stream.create_dataset(path, data=data)

    def write_attribute(self, path, name, data):
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
        self._stream[path].create(name, data)

    def __exit__(self, except_type, except_value, except_trace):
        self._stream.close()
