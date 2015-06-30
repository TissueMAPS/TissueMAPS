import yaml
import json
import os
import re

'''Utility functions for filename and path routines.'''


def regex_from_format_string(format_string):
    '''
    Convert a format string of the sort "{name}_bla/something_{number}"
    to a named regular expression a la "P<name>.*_bla/something_P<number>\d+".

    Parameters
    ----------
    format_string: str
        Python format string

    Returns
    -------
    str
        named regular expression pattern
    '''
    # Extract the names of all placeholders from the format string
    placeholders_inner_parts = re.findall(r'{(.+?)}', format_string)
    # Remove format strings
    placeholder_names = [pl.split(':')[0] for pl in placeholders_inner_parts]
    placeholder_regexes = [re.escape('{%s}' % pl) for pl in placeholders_inner_parts]

    regex = format_string
    for pl_name, pl_regex in zip(placeholder_names, placeholder_regexes):
        if re.search(r'number', pl_name):
            regex = re.sub(pl_regex, '(?P<%s>\d+)' % pl_name, regex)
        else:
            regex = re.sub(pl_regex, '(?P<%s>.*)' % pl_name, regex)

    return regex


def load_config(filename):
    '''
    Load configuration settings from YAML file.

    Parameters
    ----------
    filename: str
        name of the config file

    Returns
    -------
    dict
        YAML content

    Raises
    ------
    OSError
        when `filename` does not exist
    '''
    if not os.path.exists(filename):
        raise OSError('Configuration file does not exist: %s' % filename)
    with open(filename) as f:
        return yaml.load(f.read())


def check_config(cfg):
    '''
    Check that configuration settings contains all required keys.

    Parameters
    ----------
    cfg: dict
        configuration settings

    Raises
    ------
    KeyError
        when a required key is missing
    '''
    required_keys = {
        'COORDINATES_FROM_FILENAME',
        'COORDINATES_IN_FILENAME_ONE_BASED',
        'SUBEXPERIMENT_FOLDER_FORMAT',
        'SUBEXPERIMENT_FILE_FORMAT',
        'CYCLE_FROM_FILENAME',
        'EXPERIMENT_FROM_FILENAME',
        'IMAGE_FOLDER_LOCATION',
        'SUBEXPERIMENTS_EXIST',
        'SEGMENTATION_FOLDER_LOCATION',
        'OBJECTS_FROM_FILENAME',
        'SHIFT_FOLDER_LOCATION',
        'SHIFT_FILE_FORMAT',
        'STATS_FOLDER_LOCATION',
        'STATS_FILE_FORMAT',
        'CHANNEL_FROM_FILENAME'
    }
    for key in required_keys:
        if key not in cfg:
            raise KeyError('Configuration file must contain the key "%s"'
                           % key)


class Namespacified(object):
    '''
    Class for loading key-value pairs of a dictionary into a Namespace object.
    '''
    def __init__(self, adict):
        self.__dict__.update(adict)
