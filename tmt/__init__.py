from os.path import join, dirname, realpath
import util

try:
    from gi.repository import Vips
    vips_available = True
except ImportError as error:
    print 'Vips could not be imported.\nReason: %s' % str(error)
    vips_available = False

# Create configuration dictionary that defines default parameters
config_filename = join(dirname(realpath(__file__)), 'tmt.config')
config = util.load_config(config_filename)
util.check_config(config)

if not vips_available:
    config['USE_VIPS_LIBRARY'] = False
    print('Vips library not available. Configuration overwritten!'
          'Illuminati package will consequently not work!')
