from os.path import join, dirname, realpath
from tmt.util import load_config

version = '0.1.0'


logo = '''
     _      _         __         _          
  __| |__ _| |_ __ _ / _|_  _ __(_)___ _ _         datafusion (%(version)s)
 / _` / _` |  _/ _` |  _| || (_-< / _ \ ' \        Fuse Jterator data into one HDF5 file.
 \__,_\__,_|\__\__,_|_|  \_,_/__/_\___/_||_|       https://github.com/HackerMD/TissueMAPSToolbox

'''

# Create configuration dictionary that defines default parameters
config_filename = join(dirname(realpath(__file__)), 'datafusion.config')

config = load_config(config_filename)
