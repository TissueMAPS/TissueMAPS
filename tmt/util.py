import yaml
from os.path import exists
import re

"""
Utility functions for filename and path routines.
"""


def regex_from_format_string(format_string):
    '''
    Convert a format string of the sort
    '{name}_bla/something_{number}'
    to a named regular expression.
    '''
    # Extract the names of all placeholders from the format string
    placeholders_inner_parts = re.findall(r'{(.+?)}', format_string)
    # Remove format strings
    placeholder_names = [pl.split(':')[0] for pl in placeholders_inner_parts]
    placeholder_regexes = [re.escape('{%s}') % pl
                           for pl in placeholders_inner_parts]

    regex = format_string
    for pl_name, pl_regex in zip(placeholder_names, placeholder_regexes):
        if re.search(r'number', pl_name):
            regex = re.sub(pl_regex, '(?P<%s>\d+)' % pl_name, regex)
        else:
            regex = re.sub(pl_regex, '(?P<%s>.*)' % pl_name, regex)

    return regex


def load_config(cfg_filename):
    '''Load configuration from yaml file.'''
    if not exists(cfg_filename):
        raise Exception('Error: configuration file %s does not exist!'
                        % cfg_filename)
    return yaml.load(open(cfg_filename).read())


def check_config(cfg):
    yaml_keys = [
        'COORDINATES_FROM_FILENAME',
        'COORDINATES_IN_FILENAME_ONE_BASED',
        'SUBEXPERIMENT_FOLDER_FORMAT',
        'SUBEXPERIMENT_FILE_FORMAT',
        'CYCLE_FROM_FILENAME',
        'EXPERIMENT_FROM_FILENAME',
        'IMAGE_FOLDER_LOCATION',
        'SUBEXPERIMENTS_EXIST',
        'SEGMENTATION_FOLDER_LOCATION',
        'OBJECT_FROM_FILENAME',
        'SHIFT_FOLDER_LOCATION',
        'SHIFT_FILE_FORMAT',
        'STATS_FOLDER_LOCATION',
        'STATS_FILE_FORMAT',
        'CHANNEL_FROM_FILENAME',
        'MEASUREMENT_FOLDER_LOCATION',
        'CELL_ID_FORMAT'
    ]
    for key in yaml_keys:
        if key not in cfg:
            raise Exception('Configuration file must contain the key "%s"' % key)
