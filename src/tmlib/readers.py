import os
import sys
import h5py
import logging
'''
All readers make use of the 
`with statement context manager <https://docs.python.org/2/reference/datamodel.html#context-managers>`_.
and follow a similar syntax::

    with Reader('/path/to/folder') as reader:
        data = reader.read('name_of_file')

    with Reader() as reader:
        data = reader.read('/path/to/file')
'''

import json
import yaml
import ruamel.yaml
import traceback
import cv2
import bioformats
import javabridge
from gi.repository import Vips
from abc import ABCMeta
from abc import abstractmethod
from .errors import NotSupportedError

logger = logging.getLogger(__name__)


class Reader(object):

    '''
    Abstract base class for readers.
    '''

    __metaclass__ = ABCMeta

    def __init__(self, directory=None):
        self.directory = directory

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
    Abstract base class for reading text from files on disk.
    '''

    __metaclass__ = ABCMeta

    @abstractmethod
    def read(self, filename, **kwargs):
        pass


class XmlReader(TextReader):

    # TODO: implement xpath subset reading via lxml

    def __init__(self, directory=None):
        '''
        Initialize an object of class XmlReader.

        Parameters
        ----------
        directory: str, optional
            absolute path to a directory where files are located
        '''
        super(XmlReader, self).__init__(directory)
        self.directory = directory

    def read(self, filename, **kwargs):
        '''
        Read XML file.

        Parameters
        ----------
        filename: str
            path to the XML file
        **kwargs: dict
            additional arguments as key-value pairs (none implemented)

        Returns
        -------
        basestring
            xml string

        Note
        ----
        `filename` can be provided as relative path
        when `directory` was set upon instantiation of the reader object.

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
    Class for reading JSON from files on disk.
    '''

    def __init__(self, directory=None):
        '''
        Initialize an object of class JsonReader.

        Parameters
        ----------
        directory: str, optional
            absolute path to a directory where files are located
        '''
        super(JsonReader, self).__init__(directory)
        self.directory = directory

    def read(self, filename, **kwargs):
        '''
        Read JSON file.

        Parameters
        ----------
        filename: str
            path to the JSON file
        **kwargs: dict
            additional arguments as key-value pairs (none implemented)

        Returns
        -------
        dict or list
            file content

        Note
        ----
        `filename` can be provided as relative path
        when `directory` was set upon instantiation of the reader object.

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


class ImageMetadataReader(JsonReader):
    '''
    Class for reading image related metadata.
    '''
    def __init__(self, directory=None):
        '''
        Initialize an object of class ImageMetadataReader.

        Parameters
        ----------
        directory: str, optional
            absolute path to a directory where files are located
        '''
        super(ImageMetadataReader, self).__init__(directory)
        self.directory = directory


def load_yaml(string, use_ruamel=False):
    '''
    Convert YAML string to Python object.

    Parameters
    ----------
    string: str
        YAML string
    use_ruamel: bool, optional
        when the `ruamel.yaml` library should be used (defaults to ``False``)

    Returns
    -------
    dict or list
    '''
    if use_ruamel:
        return ruamel.yaml.load(string, ruamel.yaml.RoundTripLoader)
    else:
        return yaml.load(string)


class YamlReader(TextReader):
    '''
    Class for reading YAML from files on disk.
    '''

    def __init__(self, directory=None):
        '''
        Initialize an object of class YamlReader.

        Parameters
        ----------
        directory: str, optional
            absolute path to a directory where files are located
        '''
        super(YamlReader, self).__init__(directory)
        self.directory = directory

    def read(self, filename, **kwargs):
        '''
        Read YAML file.

        Parameters
        ----------
        filename: str
            path to the YAML file
        **kwargs: dict
            additional arguments as key-value pairs
            ("use_ruamel": *bool*, when `ruamel.yaml` library should be used)

        Returns
        -------
        dict or list
            file content

        Note
        ----
        `filename` can be provided as relative path
        when `directory` was set upon instantiation of the reader object.

        Raises
        ------
        OSError
            when `filename` does not exist
        '''
        if 'use_ruamel' in kwargs:
            use_ruamel = kwargs['use_ruamel']
        else:
            use_ruamel = False
        if self.directory:
            filename = os.path.join(self.directory, filename)
        if not os.path.exists(filename):
            raise OSError('File does not exist: %s' % filename)
        logger.debug('read file: %s', filename)
        with open(filename, 'r') as f:
            yaml_content = load_yaml(f.read(), use_ruamel)
        return yaml_content


class UserConfigurationReader(YamlReader):

    def __init__(self, directory=None):
        '''
        Initialize an object of class UserConfigurationReader.

        Parameters
        ----------
        directory: str, optional
            absolute path to a directory where files are located
        '''
        super(UserConfigurationReader, self).__init__(directory)
        self.directory = directory


class DatasetReader(object):

    '''
    Base class for reading datasets and attributes from HDF5 files on disk.
    '''

    def __init__(self, filename):
        '''
        Initialize an instance of class DatasetReader.

        Parameters
        ----------
        filename: str
            absolute path to an HDF5 file
        '''
        self.filename = filename

    def __enter__(self):
        logger.debug('read file: %s', self.filename)
        self._stream = h5py.File(self.filename, 'r')
        return self

    # TODO: raise Exception if dataset does not exist

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
        '''
        names = list()
        for name, value in self._stream[path].iteritems():
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
        '''
        names = list()
        for name, value in self._stream[path].iteritems():
            if not self._is_dataset(value):
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
        elif index is not None:
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
                    'Dataset doesn\'t have an attribute "%s": %s'
                    % (name, path))
        return attribute

    def __exit__(self, except_type, except_value, except_trace):
        self._stream.close()


class ImageReader(Reader):

    '''
    Abstract base class for reading images from files on disk.
    '''

    __metaclass__ = ABCMeta

    def __init__(self, directory=None):
        '''
        Initialize an object of class ImageReader.

        Parameters
        ----------
        directory: str, optional
            absolute path to a directory where files are located
        '''
        super(ImageReader, self).__init__(directory)
        self.directory = directory

    @abstractmethod
    def read(self, filename):
        pass

    @abstractmethod
    def read_subset(self, filename, series=None, plane=None):
        pass


class SlideReader(Reader):

    '''
    Abstract base class for reading whole slide images from files on disk.
    '''

    __metaclass__ = ABCMeta

    @abstractmethod
    def read(self, filename):
        pass

    @abstractmethod
    def split(self):
        pass


class BioformatsImageReader(ImageReader):

    '''
    Class for reading images using the
    `Bio-Formats <http://www.openmicroscopy.org/site/products/bio-formats>`_
    library.

    Note
    ----
    Requires a running Java Virtual Machine (VM). This is achieved via the
    `javabridge <http://pythonhosted.org/javabridge/start_kill.html>`_
    package.

    Warning
    -------
    Once the VM is killed it cannot be started again. This means that a second
    call of this class will fail.

    Examples
    --------
    >>> filename = '/path/to/image/file'
    >>> with BioformatsImageReader() as reader:
    ...     img = reader.read(filename)
    >>> type(img)
    numpy.ndarray
    '''

    def __init__(self, directory=None):
        '''
        Initialize an object of class BioformatsImageReader.

        Parameters
        ----------
        directory: str, optional
            absolute path to a directory where files are located
        '''
        super(BioformatsImageReader, self).__init__(directory)
        self.directory = directory

    def __enter__(self):
        # NOTE: updated "loci_tools.jar" file to latest schema:
        # http://downloads.openmicroscopy.org/bio-formats/5.1.3
        javabridge.start_vm(class_path=bioformats.JARS, run_headless=True)
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
        image = bioformats.load_image(filename, rescale=False)
        return image

    def read_subset(self, filename, series=None, plane=None):
        '''
        Read a subset of images from a file on disk.

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


class NumpyImageReader(ImageReader):

    '''
    Class for reading images from files on disk as numpy arrays.

    Uses the `OpenCV <http://docs.opencv.org>`_ library.

    Examples
    --------
    >>> filename = '/path/to/image/file'
    >>> with NumpyImageReader() as reader:
    ...     img = reader.read(filename)
    >>> type(img)
    numpy.ndarray
    '''

    def __init__(self, directory=None):
        '''
        Initialize an object of class NumpyImageReader.

        Parameters
        ----------
        directory: str, optional
            absolute path to a directory where files are located
        '''
        super(NumpyImageReader, self).__init__(directory)
        self.directory = directory

    def read(self, filename):
        '''
        Read an image from file on disk.

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
        image = cv2.imread(filename, cv2.IMREAD_UNCHANGED)
        return image

    def read_subset(self, filename, series=None, plane=None):
        '''
        If the image file contains more than one plane (band), only the first
        one will be read.
        '''
        raise AttributeError('%s doesn\'t have a "read_subset" method'
                             % self.__class__.__name__)


class VipsImageReader(ImageReader):

    '''
    Class for reading images from files on disk as Vips images.

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

    def __init__(self, directory=None):
        '''
        Initialize an object of class VipsImageReader.

        Parameters
        ----------
        directory: str, optional
            absolute path to a directory where files are located
        '''
        super(VipsImageReader, self).__init__(directory)
        self.directory = directory

    def read(self, filename):
        '''
        Read an image from file on disk.

        For details on reading images via VIPS from Python, see
        `new_from_file() <http://www.vips.ecs.soton.ac.uk/supported/current/doc/html/libvips/using-from-python.html>`_

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
        '''
        if self.directory:
            filename = os.path.join(self.directory, filename)
        if not os.path.exists(filename):
            raise OSError('Image file does not exist: %s' % filename)
        image = Vips.Image.new_from_file(filename)
        return image

    def read_subset(self, filename, series=None, plane=None):
        raise AttributeError('%s doesn\'t have a "read_subset" method. '
                             'If the file contains more than one plane/band, '
                             'only the first one will be read.'
                             % self.__class__.__name__)


class OpenslideImageReader(SlideReader):

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
        image = Vips.Image.openslideload(filename, level=0)
        return image

    def read_subset(self, filename, series_index=None, plane_index=None):
        raise AttributeError('%s doesn\'t have a "read_subset" method. '
                             'If the file contains more than one plane/band, '
                             'only the first one will be read.'
                             % self.__class__.__name__)


class WorkflowDescriptionReader(TextReader):

    def __init__(self, directory=None):
        '''
        Initialize an object of class WorkflowDescriptionReader.

        Parameters
        ----------
        directory: str, optional
            absolute path to a directory where files are located
        '''
        super(WorkflowDescriptionReader, self).__init__(directory)
        self.directory = directory

    def read(self, filename, **kwargs):
        '''
        Parameters
        ----------
        filename: str
            path to the YAML file
        **kwargs: dict
            additional arguments

        Returns
        -------
        list
            file content line by line

        Note
        ----
        `filename` can be provided as relative path
        when `directory` was set upon instantiation of the reader object.
        '''
        if self.directory:
            filename = os.path.join(self.directory, filename)
        if not os.path.exists(filename):
            raise OSError('File does not exist: %s' % filename)
        with open(filename, 'r') as f:
            content = f.read().splitlines()
        logger.debug('filter file content: remove lines that begin with "#"')
        filtered_content = [
            line for line in content
            if not line.startswith('#')
        ]
        return filtered_content


class MetadataReader(Reader):

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

    @abstractmethod
    def read(self, filename):
        pass
