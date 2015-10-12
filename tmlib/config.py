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

UPLOAD_DIR = '{experiment_dir}{sep}uploads'
UPLOAD_SUBDIR = '{upload_id}'

CYCLE_DIR = '{experiment_dir}{sep}cycles'
CYCLE_SUBDIR = '{cycle_id}'

LAYER_NAME = '{experiment_name}_t{time:0>3}_c{channel:0>3}_z{plane:0>3}'

IMAGE_UPLOAD_DIR = '{upload_subdir}{sep}image_uploads'
ADDITIONAL_UPLOAD_DIR = '{upload_subdir}{sep}additional_uploads'
OME_XML_DIR = '{upload_subdir}{sep}ome_xml'

IMAGE_DIR = '{cycle_dir}{sep}images'
IMAGE_FILE = '{experiment_name}_t{time:0>3}_{well_id}_y{well_y:0>3}_x{well_x:0>3}_c{channel:0>3}_z{plane:0>3}.png'

IMAGE_METADATA_FILE = 'image_metadata.ome.xml'
ALIGN_DESCRIPTOR_FILE = 'alignment_description.json'

STATS_DIR = '{cycle_dir}{sep}stats'
STATS_FILE = '{channel}.stat.h5'
