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
