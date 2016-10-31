# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
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
import traceback
import openslide
from tmlib.readers import MetadataReader
from tmlib.errors import NotSupportedError


class OpenslideMetadataReader(MetadataReader):

    def read(self, filename):
        '''Reads metadata from whole slide images.

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
