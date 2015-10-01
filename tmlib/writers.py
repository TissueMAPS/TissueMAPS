import sys
import h5py
import numpy as np
import logging
import json
import yaml
import ruamel.yaml
import traceback
from abc import ABCMeta
from abc import abstractmethod

logger = logging.getLogger(__name__)

'''
Writer Classes.


All writers make use of the 
`with statement context manager <https://docs.python.org/2/reference/datamodel.html#context-managers>`_.
and thus follow a similar syntax::

    with WriterClass('/path/to/directory') as reader:
        reader.read('name_of_file')
'''


class Writer(object):
    '''
    Abstract base class for a Writer.
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
    def write(self, filename, data):
        pass


class JsonWriter(TextWriter):

    def __init__(self, directory):
        '''
        Instantiate an object of class JsonWriter.

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
            description that should be written to file
        **kwargs: dict
            additional arguments
            ("naicify": *bool*, whether `data` should be naicely formatted)

        Note
        ----
        `filename` will be truncated in case it already exists.
        '''
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


class ImageMetadataWriter(JsonWriter):
    '''
    Class for reading image related metadata.
    '''
    def __init__(self, directory=None):
        '''
        Instantiate an object of class ImageMetadataWriter.

        Parameters
        ----------
        directory: str, optional
            absolute path to a directory where files are located
        '''
        super(ImageMetadataWriter, self).__init__(directory)
        self.directory = directory


class JobDescriptionWriter(JsonWriter):
    '''
    Class for reading image related metadata.
    '''
    def __init__(self, directory=None):
        '''
        Instantiate an object of class JobDescriptionWriter.

        Parameters
        ----------
        directory: str, optional
            absolute path to a directory where files are located
        '''
        super(JobDescriptionWriter, self).__init__(directory)
        self.directory = directory


class ShiftDescriptionWriter(JsonWriter):
    '''
    Class for reading image related metadata.
    '''
    def __init__(self, directory=None):
        '''
        Instantiate an object of class ShiftDescriptionWriter.

        Parameters
        ----------
        directory: str, optional
            absolute path to a directory where files are located
        '''
        super(ShiftDescriptionWriter, self).__init__(directory)
        self.directory = directory


class SupportedFormatsWriter(JsonWriter):
    '''
    Class for reading image related metadata.
    '''
    def __init__(self, directory=None):
        '''
        Instantiate an object of class SupportedFormatsWriter.

        Parameters
        ----------
        directory: str, optional
            absolute path to a directory where files are located
        '''
        super(SupportedFormatsWriter, self).__init__(directory)
        self.directory = directory


class YamlWriter(TextWriter):

    def __init__(self, directory):
        '''
        Instantiate an object of class YamlWriter.

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
            description that should be written to file
        **kwargs: dict
            additional arguments
            ("use_ruamel": *bool*, when `ruamel.yaml` library should be used)


        Note
        ----
        `filename` will be truncated in case it already exists.
        '''
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
                f.write(yaml.dump(data,
                        default_flow_style=False,
                        explicit_start=True))


class PipeWriter(JsonWriter):
    '''
    Class for reading image related metadata.
    '''
    def __init__(self, directory=None):
        '''
        Instantiate an object of class PipeWriter.

        Parameters
        ----------
        directory: str, optional
            absolute path to a directory where files are located
        '''
        super(PipeWriter, self).__init__(directory)
        self.directory = directory


class HandlesWriter(JsonWriter):
    '''
    Class for reading image related metadata.
    '''
    def __init__(self, directory=None):
        '''
        Instantiate an object of class HandlesWriter.

        Parameters
        ----------
        directory: str, optional
            absolute path to a directory where files are located
        '''
        super(HandlesWriter, self).__init__(directory)
        self.directory = directory


class DatasetWriter(object):

    '''
    Base class for writing datasets and attributes to HDF5 files on disk.
    '''

    def __init__(self, filename, new=False):
        '''
        Instantiate an instance of class DatasetWriter.

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
        if ((isinstance(data, np.ndarray) or isinstance(data, list))
                and all([isinstance(d, basestring) for d in data])):
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

