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
    data: dataist[list]

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
    data: dataist[str]

    Returns
    -------
    str
    '''
    # NOTE: code taken from stackoverflow.com (question 2892931)
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


def is_number(s):
    '''
    Check whether a string can be represented by a number.

    Parameters
    ----------
    s: str

    Returns
    -------
    bool

    Examples
    --------
    >>>is_number('blabla')
    False
    >>>is_number('007')
    True
    '''
    # NOTE: code taken from stackoverflow.com (question 354038)
    try:
        float(s)
        return True
    except ValueError:
        return False


def map_letter_to_number(letter):
    '''
    Map capital letter to number.

    Parameters
    ----------
    letter: str
        capital letter

    Returns
    -------
    int
        one-based index number

    Examples
    --------
    >>>map_letter_to_number("A")
    1
    '''
    return ord(letter) - 64


def map_number_to_letter(number):
    '''
    Map number to capital letter.

    Parameters
    ----------
    number: int
        one-based index number

    Returns
    -------
    str
        capital letter

    Examples
    --------
    >>>map_number_to_letter(1)
    "A"
    '''
    return chr(number+64)


def missing_elements(data, start=None, end=None):
    '''
    Determine missing elements in a sequence of integers.

    Parameters
    ----------
    data: List[int]
        sequence with potentially missing elements
    start: int, optional
        lower limit of the range (defaults to ``0``)
    end: int, optional
        upper limit of the range (defaults to ``len(data)-1``)

    Examples
    --------
    >>>data = [10, 12, 13, 15, 16, 19, 20]
    >>>list(missing_elements(data))
    [11, 14, 17, 18]
    '''
    # NOTE: code adapted from stackoverflow.com (question 16974047)
    if not start:
        start = 0
    if not end:
        end = len(data)-1

    if end - start <= 1: 
        if data[end] - data[start] > 1:
            for d in range(data[start] + 1, data[end]):
                yield d
        return

    index = start + (end - start) // 2

    # is the lower half consecutive?
    consecutive_low =  data[index] == data[start] + (index - start)
    if not consecutive_low:
        for s in missing_elements(data, start, index):
            yield s

    # is the upper part consecutive?
    consecutive_high =  data[index] == data[end] - (end - index)
    if not consecutive_high:
        for e in missing_elements(data, index, end):
            yield e
