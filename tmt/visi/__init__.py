from os.path import join, dirname, realpath
from tmt.util import load_config
from visi.util import check_visi_config

version = '0.1.0'

# Create configuration dictionary that defines default parameters
config_filename = join(dirname(realpath(__file__)), 'visi.config')

config = load_config(config_filename)
check_visi_config(config)
