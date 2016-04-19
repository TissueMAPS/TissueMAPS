from tmlib import __version__

__fullname__ = 'Image analysis pipeline engine'

__desription__ = '''Application of a sequence of algorithms to a set of images
    to segment the images and extract features for the identified objects.
'''

__logo__ = '''
    _ _                _
   (_) |_ ___ _ _ __ _| |_ ___ _ _      {name} ({version})
   | |  _/ -_) '_/ _` |  _/ _ \ '_|     {fullname}
  _/ |\__\___|_| \__,_|\__\___/_|       https://github.com/TissueMAPS/TmLibrary
 |__/
'''.format(name=__name__, version=__version__, fullname=__fullname__)
