import sys
import traceback
import openslide
from ..readers import MetadataReader
from ..errors import NotSupportedError


class OpenslideMetadataReader(MetadataReader):

    def read(self, filename):
        '''
        Read metadata from whole slide images.

        For details on reading metadata via openslide from Python, see
        `online documentation <http://openslide.org/api/python/>`_.

        Parameters
        ----------
        filename: str
            absolute path to the file

        Returns
        -------
        openslide.OpenSlide
            image metadata

        Raises
        ------
        NotSupportedError
            when the file format is not supported
        '''
        metadata = openslide.OpenSlide(filename)
        return metadata

    def __exit__(self, except_type, except_value, except_trace):
        if except_type is openslide.OpenSlideUnsupportedFormatError:
            raise NotSupportedError('File format is not supported.')
        if except_type is openslide.OpenSlideError:
            sys.stdout.write('The following error occurred:\n%s'
                             % str(except_value))
            for tb in traceback.format_tb(except_trace):
                sys.stdout.write(tb)
