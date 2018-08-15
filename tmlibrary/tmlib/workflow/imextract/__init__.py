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
'''Workflow step for extraction of pixel data from microscopy image files.

Microscopes usually store pixel data together with related acquisition metadata
in vendor-specific formats. Image files may contain more than one pixel plane.
Some microscopes even store all planes in a single file. This is not practical
and may even become a bottleneck depending on file access patterns and
implemented storage backend. These used file formates are also often not
understood by standard readers and generally not optimized for scalable storage
in a distributed computing environment. In addition, microscopes typically
store images uncompressed, while it is often desirable to apply compression to
reduce storage requirements. To meet these ends, the `imextract` step extracts
each pixel plane from microscope files and stores them in a consistent way,
which facilitate downstream processing.

Note that implementation details of the storage backend may be subject to
change and files may not necessarily be accessible via a POSIX compliant file
system! Users are therefore advised to use
:meth:`ChannelImageFile.get <tmlib.models.ChannelImageFile.get>`
to retrieve the extraced images.

Warning
-------
This step (at least temporarily) approximately doubles storage requirements,
because pixel data are extracted in parallel during the *run* phase,
but the microscope image files are only deleted afterwards during the
*collect* phase (and only if the 
:attr:`delete <tmlib.workflow.imextract.ImextractBatchArguments.delete>`
argument is set to ``True``).
'''
from tmlib import __version__

__dependencies__ = {'metaconfig'}

__fullname__ = 'Extration of pixel data from microscopy image files'

__description__ = (
    'Extracts pixel elements from heterogeneous '
    'microscopy image file formats based on the configured image metadata '
    'and stores them in a standardized file format.'
)

__logo__ = '''
  _               _               _
 (_)_ __  _____ _| |_ _ _ __ _ __| |_      {name} ({version})
 | | '  \/ -_) \ /  _| '_/ _` / _|  _|     {fullname}
 |_|_|_|_\___/_\_\\\__|_| \__,_\__|\__|     https://github.com/TissueMAPS/TmLibrary
'''.format(name=__name__, version=__version__, fullname=__fullname__)
