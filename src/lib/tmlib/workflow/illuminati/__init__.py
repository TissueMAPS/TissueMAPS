'''Workflow step for creation of pyramid images.

To achieve efficient zoomable visualization of terabyte-size microscopy image
dataasets accross multiple resolution levels, images need to be represented in
`pyramid <https://en.wikipedia.org/wiki/Pyramid_(image_processing)>` _ format.
To this end, the `illuminati` step casts images to 8-bit and tiles them up
according to available positional information.
Users further have the option to correct images for illumination artifacts and
align them between acquisitions based on pre-calculated statistics (if
available).

'''
from tmlib import __version__


__dependencies__ = {'imextract'}

__optional_dependencies__ = {'align', 'corilla'}

__fullname__ = 'Pyramid image builder'

__description__ = '''Creation of pyramids for interactive, web-based
    visualization of images.
'''

__logo__ = u'''
   .
   I        {name} ({version})
  LLU       {fullname}
 MINATI     https://github.com/TissueMAPS/TmLibrary
'''.format(name=__name__, version=__version__, fullname=__fullname__)
