from os.path import join, dirname, realpath
import utils

# Create configuration dictionary that defines default parameters
cfg_filename = join(dirname(realpath(__file__)), 'tmt.cfg')
cfg = utils.read_yaml(cfg_filename)
