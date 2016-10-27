'''Workflow step for registration and alignment of microscopy images.

When images are acquired at the different time points they may exhibit a
displacement relative to each other. To overlay these image for visualization
or analysis, they need to be registered and aligned between acquisitions.
To this end, the `align` step computes translational shifts of each image
acquired at the same site relative to one reference image (by default the
one of the first acquisition time point). The computed shift values are stored
and can later be applied for alignment.
Note that translations are computed only per site and no attempt is made to
find a globally optimal alignment. This is done for performance reasons and
to simplify parallelization.
'''
from tmlib import __version__

__dependencies__ = {'imextract'}

__fullname__ = 'Align images between acquisitions'

__description__ = '''Registration of images acquired in different multiplexing
    cycles relative to a reference cycle. The calculated shifts can then
    subsequently be used to align images.
'''

__logo__ = u'''
       _ _
  __ _| (_)__ _ _ _         {name} ({version})
 / _` | | / _` | ' \        {fullname}
 \__,_|_|_\__, |_||_|       https://github.com/TissueMAPS/TmLibrary
          |___/
'''.format(name=__name__, version=__version__, fullname=__fullname__)
