from os.path import join, dirname, realpath
import util

# Create configuration dictionary that defines default parameters
config_filename = join(dirname(realpath(__file__)), 'image_toolbox.config')
config = util.load_config(config_filename)
util.check_config(config)
