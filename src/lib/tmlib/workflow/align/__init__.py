from tmlib import __version__

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
