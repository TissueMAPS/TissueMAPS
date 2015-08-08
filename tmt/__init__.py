from os.path import join, dirname, realpath
import utils

# Create configuration dictionary that defines default parameters
config_filename = join(dirname(realpath(__file__)), 'tmt.config')
config = utils.load_config(config_filename)
# utils.check_config(config)
