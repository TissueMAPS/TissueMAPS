import re
import os

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


def indices(data, item):
    '''
    Determine all indices of an item in a list.

    Parameters
    ----------
    data: list
    item:
        the element whose index position should be determined

    Returns
    -------
    list
        all indices of `item` in `data`
    '''
    start_at = -1
    locs = []
    while True:
        try:
            loc = data.index(item, start_at+1)
        except ValueError:
            break
        else:
            locs.append(loc)
            start_at = loc
    return locs


def flatten(data):
    '''
    Transform a list of lists into a flat list.

    Parameters
    ----------
    data: List[list]

    Returns
    -------
    list
    '''
    return [item for sublist in data for item in sublist]


def common_substring(data):
    '''
    Find longest common substring across a collection of strings.

    Parameters
    ----------
    data: List[str]

    Returns
    -------
    str
    '''
    # NOTE: code taken from stackoverflow (question 2892931)
    substr = ''
    if len(data) > 1 and len(data[0]) > 0:
        for i in range(len(data[0])):
            for j in range(len(data[0])-i+1):
                if j > len(substr) and all(data[0][i:i+j] in x for x in data):
                    substr = data[0][i:i+j]
    return substr


def list_directory_tree(start_dir):
    '''
    Capture the whole directory tree downstream of `start_dir`.

    Parameters
    ----------
    start_dir: str
        absolute path to the directory whose content should be listed
    '''
    for root, dirs, files in os.walk(start_dir):
        level = root.replace(start_dir, '').count(os.sep)
        indent = ' ' * 4 * (level)
        print('{}{}/'.format(indent, os.path.basename(root)))
