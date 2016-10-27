'''Workflow step for extraction of microscope image metadata.

Microscopes typically write metadata about the image acquisition process into
the header of the generated image files. Unfortunately, almost every vendor
uses a custom file format. The `metaextract` step uses the
`Bio-Formats <https://www.openmicroscopy.org/site/products/bio-formats>`_
library to extract metadata from heterogeneous image file formats in form of
`OMEXML <https://www.openmicroscopy.org/site/support/ome-model/ome-xml/index.html>`_
according to the standardized
`OME <https://www.openmicroscopy.org/site/support/ome-model/>`_ data model.

'''
from tmlib import __version__

__dependencies__ = {}

__fullname__ = 'Extraction of image metadata'

__description__ = '''Extraction of OMEXML metadata from heterogeneous
    microscopy image file formats.
'''

__logo__ = '''
            _                _               _
  _ __  ___| |_ __ _ _____ _| |_ _ _ __ _ __| |_    {name} ({version})
 | '  \/ -_)  _/ _` / -_) \ /  _| '_/ _` / _|  _|   {fullname}
 |_|_|_\___|\__\__,_\___/_\_\\\__|_| \__,_\__|\__|   https://github.com/TissueMAPS/TmLibrary
'''.format(name=__name__, version=__version__, fullname=__fullname__)



