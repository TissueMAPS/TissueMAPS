import yaml
import cv2
from gi.repository import Vips
import bioformats as bf
import javabridge


class ImageReader(object):

    '''
    Class for reading images from files on disk.

    Supported are readers of the following image processing libraries:
        - `OpenCV <http://docs.opencv.org/modules/highgui/doc/reading_and_writing_images_and_video.html#imread>`_
        - `Vips <http://www.vips.ecs.soton.ac.uk/supported/current/doc/html/libvips/using-from-python.html>`_
        - `Bio-Formats <http://pythonhosted.org/python-bioformats/#reading-images>`_

    Examples
    --------
    >>> filename = '/path/to/image/file'
    >>> with ImageReader('bioformats') as reader:
    ...     img = reader.read(filename)
    >>> type(img)
    numpy.ndarray
    '''

    readers = {'opencv', 'bioformats', 'vips'}

    def __init__(self, reader):
        '''
        Initialize an instance of class ImageReader.

        Parameters
        ----------
        reader: str
            image processing library to use for reading the image
            ("opencv", "bioformats", "vips")

        Raises
        ------
        ValueError
            when `reader` is invalid, i.e. not supported
        '''
        self.reader = reader
        if self.reader not in ImageReader.readers:
            raise ValueError('"%s" is not a valid reader. '
                             'Supported readers are: "%s".'
                             % (self.reader, '", "'.join(ImageReader.readers)))

    def __enter__(self):
        if self.reader == 'bioformats':
            # NOTE: updated "loci_tools.jar" file to latest schema:
            # http://downloads.openmicroscopy.org/bio-formats/5.1.3
            javabridge.start_vm(class_path=bf.JARS, run_headless=True)
        return self

    def read(self, filename):
        '''
        Read an image from file on disk.

        Parameters
        ----------
        filename: str
            absolute path to the image file

        Returns
        -------
        numpy.ndarray or Vips.Image
            image
        '''
        if self.reader == 'opencv':
            self.image = cv2.imread(filename, cv2.IMREAD_UNCHANGED)
        elif self.reader == 'bioformats':
            self.image = bf.load_image(filename)
        elif self.reader == 'vips':
            self.image = Vips.Image.new_from_file(filename)
        return self.image

    def __exit__(self, type, value, traceback):
        if self.reader == 'bioformats':
            javabridge.kill_vm()


class MetadataReader(object):

    '''
    Class for reading metadata for images from YAML files on disk.

    Examples
    --------
    >>> filename = '/path/to/metadata/file'
    >>> with MetadataReader() as metadata_file:
    ...     metadata = image_file.read(filename)
    >>> type(metadata)
    dict
    '''

    def __enter__(self):
        return self

    def read(self, filename):
        '''
        Read a metadata file from disk.

        Parameters
        ----------
        filename: str
            name of the metadata file

        Returns
        -------
        Dict[str, Dict[str, int or str]]
            metadata
        '''
        with open(filename, 'r') as f:
            content = f.read()
        self.metadata = yaml.load(content)
        return self.metadata

    def __exit__(self, type, value, traceback):
        pass


def read_yaml(filename):
    '''
    Read YAML file.

    Parameters
    ----------
    filename: str
        absolute path to the YAML file

    Returns
    -------
    dict or list
        file content
    '''
    with open(filename, 'r') as f:
        file_content = f.read()
    yaml_content = yaml.load(file_content)
    return yaml_content

