from os.path import join, dirname, realpath
from tmt.utils import load_config

__version__ = '0.1.0'


logo = u'''
     _       __
  __| |__ _ / _|_  _         dafu (%(version)s)
 / _` / _` |  _| || |        DAta FUsion for Jterator projects.
 \__,_\__,_|_|  \_,_|        https://github.com/HackerMD/TissueMAPSToolbox

'''

# Create configuration dictionary that defines default parameters
config_filename = join(dirname(realpath(__file__)), 'dafu.config')

config = load_config(config_filename)
