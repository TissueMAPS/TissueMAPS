import yaml
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
    format_string = re.sub(r'\.', '\.', format_string)  # escape dot
    placeholders_inner_parts = re.findall(r'{(.+?)}', format_string)
    # Remove format strings
    placeholder_names = [pl.split(':')[0] for pl in placeholders_inner_parts]
    placeholder_regexes = [re.escape('{%s}' % pl)
                           for pl in placeholders_inner_parts]

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
        'SUBEXPERIMENTS_EXIST',
        'COORDINATES_IN_FILENAME_ONE_BASED',
        'USE_VIPS_LIBRARY',
        'INFO_FROM_FILENAME',
        'SUBEXPERIMENT_FOLDER_FORMAT',
        'IMAGE_FOLDER_FORMAT',
        'IMAGE_FILE_FORMAT',
        'IMAGE_INFO_FILE_FORMAT',
        'SEGMENTATION_FOLDER_FORMAT',
        'SEGMENTATION_FILE_FORMAT',
        'SEGMENTATION_INFO_FILE_FORMAT',
        'SHIFT_FOLDER_FORMAT',
        'SHIFT_FILE_FORMAT',
        'STATS_FOLDER_FORMAT',
        'STATS_FILE_FORMAT'
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
