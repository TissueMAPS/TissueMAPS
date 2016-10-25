from tmlib import __version__


__fullname__ = 'Correction of illumination artifacts'

__description__ = '''Calculation of illumination statistics over a set of
    images belonging to the same channel. The resulting statistics can
    subsequently be applied to individual images to correct them for
    illumination artifacts.
'''

__logo__ = u'''
             _ _ _
  __ ___ _ _(_) | |__ _     {name} ({version})
 / _/ _ \ '_| | | / _` |    {fullname}
 \__\___/_| |_|_|_\__,_|    https://github.com/TissueMAPS/TmLibrary
'''.format(name=__name__, version=__version__, fullname=__fullname__)
