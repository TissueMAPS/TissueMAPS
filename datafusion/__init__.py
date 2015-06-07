from os.path import join, dirname, realpath
from image_toolbox.util import load_config

version = '0.1.0'

# Create configuration dictionary that defines default parameters
config_filename = join(dirname(realpath(__file__)), 'datafusion.config')

config = load_config(config_filename)
