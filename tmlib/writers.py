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
                f.write(yaml.dump(data,
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
        '''
        super(ImageWriter, self).__init__(directory)
        self.directory = directory

    def write(self, filename, data, **kwargs):
        '''
        Write an image to file.

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
        if isinstance(data, np.ndarray) and data.dtype == 'O':
            logger.debug('write dataset "%s" as variable length', path)
            self._write_vlen(path, data)
        else:
            logger.debug('write dataset "%s"', path)
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

