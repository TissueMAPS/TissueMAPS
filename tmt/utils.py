import yaml
import json
import os
import re

'''Utility functions for standard routines.'''


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


def write_yaml(filename, data):
    '''
    Write data to YAML file.

    Parameters
    ----------
    filename: str
        name of the YAML file
    data: list or dict
        description that should be written to file
    '''
    with open(filename, 'w') as f:
        f.write(yaml.safe_dump(data, default_flow_style=False))


def load_yaml(stream):
    '''
    Load YAML from open file stream.

    Parameters
    ----------
    stream: file object
        open file as obtained with ``open()``

    Returns
    -------
    dict or list
        file content
    '''
    return yaml.safe_load(stream.read())


def read_yaml(filename):
    '''
    Read YAML file.

    Parameters
    ----------
    filename: str
        absolute path to the YAML file

    Returns
    -------
    dict or list
        file content

    Raises
    ------
    OSError
        when `filename` does not exist
    '''
    if not os.path.exists(filename):
        raise OSError('File does not exist: %s' % filename)
    with open(filename, 'r') as f:
        yaml_content = load_yaml(f)
    return yaml_content


def write_json(filename, data):
    '''
    Write data to JSON file.

    Parameters
    ----------
    filename: str
        name of the JSON file
    data: list or dict
        description that should be written to file
    '''
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4, separators=(',', ': '), sort_keys=True)


def read_json(filename):
    '''
    Read data from JSON file.

    Parameters
    ----------
    filename: str
        name of the JSON file

    Returns
    -------
    dict or list
        content of the JSON file

    Raises
    ------
    OSError
        when `filename` does not exist
    '''
    if not os.path.exists(filename):
        raise OSError('File does not exist: %s' % filename)
    with open(filename, 'r') as f:
        file_content = f.read()
    json_content = json.loads(file_content)
    return json_content


def indices(seq, item):
    '''
    Determine all indices of an item in a list.

    Parameters
    ----------
    seq: list
    item:
        the element whose index position should be determined

    Returns
    -------
    list
        all indices of `item` in `seq`
    '''
    start_at = -1
    locs = []
    while True:
        try:
            loc = seq.index(item, start_at+1)
        except ValueError:
            break
        else:
            locs.append(loc)
            start_at = loc
    return locs


def flatten(seq):
    '''
    Flatten a list of lists into a list.

    Parameters
    ----------
    seq: List[list]

    Returns
    -------
    list
    '''
    return [item for sublist in seq for item in sublist]
