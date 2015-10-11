'''
CONFIGURATION SETTINGS

Describe the experimental layout (directory structure and filename nomenclature)
by Python format strings. The keywords are replaced by the program with the
values of attributes of the configuration classes::

* *experiment_dir*: Absolute path to the experiment_name folder (string).

* *experiment_name*: Name of the experiment folder, i.e. the basename of "experiment_dir" (string).
                 
* *cycle_dir*: Absolute path to the cycle directory (string).

* *cycle_name*: Name of the cycle folder, i.e. the basename of "cycle_dir" (string).

* *channel_name*: Name of the corresponding channel or wavelength (string).

* *channel_id*: Zero-based channel identifier number (integer).

* *site_id*: Zero-based acquisition site identifier number (integer).

* *time_id*: Zero-based time point identifier number (integer).

* *plane_id*: Zero-based focal plane identifier number (integer).

* *well_id*: Well identifier sting (string).

* *sep*: Platform-specific path separator ("/" Unix or "\" Windows)
'''

LAYERS_DIR = '{experiment_dir}{sep}layers'
DATA_FILE = '{experiment_dir}{sep}{experiment_name}.data.h5'

USER_CFG_FILE = '{experiment_dir}{sep}user.cfg.yml'

CYCLE_DIR = '{experiment_name}_{cycle_id}'
UPLOAD_DIR = '{experiment_dir}{sep}uploads'
UPLOAD_SUBDIR = '{cycle_id}'
LAYER_NAME = '{experiment_name}_t{time:0>3}_c{channel:0>3}_z{plane:0>3}'

IMAGE_UPLOAD_DIR = '{upload_subdir}{sep}image_uploads'
ADDITIONAL_UPLOAD_DIR = '{upload_subdir}{sep}additional_uploads'
OME_XML_DIR = '{upload_subdir}{sep}ome_xml'
IMAGE_UPLOAD_IMGMAPPER_FILE = '{upload_name}_file_mapper.json'
IMAGE_UPLOAD_METADATA_FILE = '{upload_name}_configured_metadata.ome.xml'

IMAGE_DIR = '{cycle_dir}{sep}images'
IMAGE_FILE = '{experiment_name}_t{time:0>3}_w{well:0>3}_s{site:0>4}_c{channel:0>3}_z{plane:0>3}.png'

IMAGE_METADATA_FILE = '{cycle_name}.ome.xml'
ALIGN_DESCRIPTOR_FILE = '{cycle_name}.align.json'

STATS_DIR = '{cycle_dir}{sep}stats'
STATS_FILE = '{cycle}_{channel}.stat.h5'
