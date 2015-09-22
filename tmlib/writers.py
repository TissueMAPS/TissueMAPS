import h5py
import numpy as np


class DatasetWriter(object):

    '''
    Base class for writing datasets and attributes to HDF5 files on disk.
    '''

    def __init__(self, filename, new=False):
        '''
        Initialize an instance of class DatasetWriter.

        Parameters
        ----------
        filename: str
            absolute path to HDF5 file
        new: bool, optional
            whether a new file should be created, i.e. existing files should be
            overwritten
        '''
        self.filename = filename
        self.new = new

    def __enter__(self):
        if self.new:
            self._stream = h5py.File(self.filename, 'w')
        else:
            self._stream = h5py.File(self.filename, 'a')
        return self

    def write(self, path, data):
        '''
        Create a dataset.

        Parameters
        ----------
        path: str
            absolute path to the dataset within the file
        data:
            dataset; will be put through ``numpy.array(data)``

        Note
        ----
        If `data` is a nested list or array of arrays,
        a *variable_length* dataset with dimensions ``(len(data),)`` is
        created. For more information on *variable-length* types, see
        `h5py docs <http://docs.h5py.org/en/latest/special.html>`_.
        '''
        if isinstance(data, basestring):
            data = np.string_(data)
        if any([isinstance(d, basestring) for d in data]):
            data = [np.string_(d) for d in data]
        if isinstance(data, list):
            data = np.array(data)
        if (isinstance(data, np.ndarray)
                and all([isinstance(d, np.ndarray) for d in data])
                and len(data.shape) == 1):
            # TODO: is this general enough? update Note in docstring
            self._write_vlen(path, data)
        else:
            self._stream.create_dataset(path, data=data)

    def _write_vlen(self, path, data):
        data_type = np.unique([d.dtype for d in data])
        if len(data_type) == 0:
            dt = h5py.special_dtype(vlen=np.int64)
        else:
            dt = h5py.special_dtype(vlen=data_type[0])
        dataset = self._stream.create_dataset(path, (len(data),), dtype=dt)
        for i, d in enumerate(data):
            dataset[i] = d

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
        self._stream[path].create(name, data)

    def __exit__(self, except_type, except_value, except_trace):
        self._stream.close()
