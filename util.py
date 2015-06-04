import os
import yaml

def load_config(config_filename):
    '''Load configuration from yaml file.'''
    if not os.path.exists(config_filename):
        raise Exception('Error: configuration file %s does not exist!'
                        % config_filename)
    return yaml.load(open(config_filename).read())


def check_config(config):
    yaml_keys = [
        'COORDINATE_FROM_FILENAME',
        'COORDINATES_IN_FILENAME_ONE_BASED',
        'SHIFT_DESCRIPTOR_FILE_LOCATION',
        'CYCLE_SUBDIRECTORY_NAME_FORMAT',
        'CYCLE_NR_FROM_FILENAME',
        'EXPERIMENT_NAME_FROM_FILENAME',
        'IMAGE_FOLDER_LOCATION',
        'SEGMENTATION_FOLDER_LOCATION',
        'SHIFT_FOLDER_LOCATION',
        'STATS_FOLDER_LOCATION',
        'STATS_FILE_FORMAT',
        'CHANNEL_NR_FROM_FILENAME',
        'MEASUREMENT_FOLDER_LOCATION',
        'CELL_ID_FORMAT'
    ]
    for key in yaml_keys:
        if key not in config:
            print('Error: configuration file must contain the key "%s"' % key)
