from os.path import join, dirname, realpath
from . import utils
# import logging

# Create configuration dictionary that defines default parameters
cfg_filename = join(dirname(realpath(__file__)), 'tmlib.cfg')
cfg = utils.read_yaml(cfg_filename)
