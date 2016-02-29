'''Decorators and other utility functions.'''

import time
import datetime
import re
import os
import inspect
import types  # require for type checks
from types import *
import logging

logger = logging.getLogger(__name__)


def create_datetimestamp():
    '''
    Create a datetimestamp in the form "year-month-day_hour:minute:second".
    
    Returns
    -------
    str
        datetimestamp
    '''
    t = time.time()
    return datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d_%H-%M-%S')


def create_timestamp():
    '''
    Create a timestamp in the form "hour:minute:second".

    Returns
    -------
    str
        timestamp
    '''
    t = time.time()
    return datetime.datetime.fromtimestamp(t).strftime('%H-%M-%S')


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
    consecutive_low = data[index] == data[start] + (index - start)
    if not consecutive_low:
        for s in missing_elements(data, start, index):
            yield s

    # is the upper part consecutive?
    consecutive_high = data[index] == data[end] - (end - index)
    if not consecutive_high:
        for e in missing_elements(data, index, end):
            yield e


def assert_type(**expected):
    '''
    Decorator function that asserts that the type of function arguments.

    Parameters
    ----------
    expected: Dict[str, type or Set[type]], optional
        key-value pairs of names and expected types
        of each argument that should be checked

    Raises
    ------
    ValueError
        when a name is provided that is not an argument of the function
    TypeError
        when type of the function argument doesn't match the expected type

    Examples
    --------
    from tmlib.utils import assert_type
    import types

    class TypeCheckExample(object):

        @assert_type(value1=str, value2={int, float, types.NoneType})
        def test(self, value1, value2=None):
            print 'value1: "%s"' % value1
            if value2:
                print 'value2: %d' % value2

    example = TypeCheckExample()
    example.test('blabla', 2)
    example.test('blabla', 2.0)
    example.test('blabla')
    example.test('blabla', '2')  # raises TypeError
    '''
    def decorator(func):
        # TODO: use importlib for non-buildin types
        def wrapper(*args, **kwargs):
            inputs = inspect.getargspec(func)
            for expected_name, expected_type in expected.iteritems():
                if expected_name not in inputs.args:
                    raise ValueError('Unknown argument "%s"' % expected_name)
                index = inputs.args.index(expected_name)
                if index >= len(args):
                    continue
                ets = set()
                if isinstance(expected_type, type):
                    ets = {expected_type}
                elif isinstance(expected_type, set):
                    ets = expected_type
                elif isinstance(expected_type, list):
                    ets = set(expected_type)
                if not any([isinstance(args[index], et) for et in ets]):
                    options = ' or '.join([et.__name__ for et in ets])
                    raise TypeError('Argument "%s" must have type %s.' %
                                    (expected_name, options))
            return func(*args, **kwargs)

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

    return decorator


def assert_path_exists(*expected):
    '''
    Decorator function that asserts that a path to a file or directory on disk
    specified by a function argument exists.

    Parameters
    ----------
    expected: List[str], optional
        names of arguments that should be checked

    Raises
    ------
    ValueError
        when a name is provided that is not an argument of the function
    OSError
        when the path specified by the function argument doesn't exists on disk

    Examples
    --------
    from tmlib.utils import assert_path_exists
    import os

    class LocationCheckExample(object):

        @assert_path_exists('value1')
        def test(self, value1, value2=None):
            print 'content of directory "%s":\n%s' % (value1, os.listdir(value1))

    example = LocationCheckExample()
    example.test('/tmp')
    example.test('/blabla')  # raises OSError
    '''
    def decorator(func):
        inputs = inspect.getargspec(func)

        def wrapper(*args, **kwargs):
            for expected_name in expected:
                if expected_name not in inputs.args:
                    raise ValueError('Unknown argument "%s"' % expected_name)
                index = inputs.args.index(expected_name)
                if index >= len(args):
                    continue
                location = args[index]
                if not os.path.exists(location):
                    raise OSError('Location specified by argument "%s" '
                                  'does\'t exist: "%s"' %
                                  (expected_name, location))
                elif os.access(os.path.dirname(location), os.W_OK):
                    raise OSError('Location specified by argument "%s" '
                                  'doesn\'t have write permissions: "%s"' %
                                  (expected_name, location))
            return func(*args, **kwargs)

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

    return decorator


class autocreate_directory_property(object):

    '''
    Decorator class that acts like a property.
    The value represents a path to a directory on disk. The directory is
    automatically created when it doesn't exist. Once created the value
    is cached, so that there is no reattempt to create the directory.

    Raises
    ------
    TypeError
        when the value of the property doesn't have type basestring
    ValueError
        when the value of the property is empty
    OSError
        when the parent directory does not exist

    Examples
    --------
    from tmlib.utils import autocreate_directory_property
    
    class AutocreateExample(object):

        @autocreate_directory_property
        def my_new_directory(self):
            return '/tmp/blabla'

    example = AutocreateExample()
    example.my_new_directory
    '''
    def __init__(self, func):
        self.__doc__ = func.__doc__
        self.func = func

    def __get__(self, obj, cls):
        if obj is None:
            return self
        value = obj.__dict__[self.func.__name__] = self.func(obj)
        if not isinstance(value, basestring):
            raise TypeError('Value of property "%s" must have type basestring.'
                            % value)
        if not value:
            raise ValueError('Value of property "%s" cannot be empty.'
                             % value)
        if not os.path.exists(os.path.dirname(value)):
            raise OSError('Value of property "%s" must be a valid path.'
                          % value)
        if not os.path.exists(value):
            logger.debug('create directory: %s')
            os.mkdir(value)
        return value


def same_docstring_as(ref_func):
    '''
    Decorator function that sets the docstring of the decorate function
    to the one of `ref_func`.
    This is helpful for methods of derived classes that should "inherit"
    the docstring of the abstract method in the base class.

    Parameters
    ----------
    ref_func: function
        reference function from which the docstring should be copied
    '''

    def decorator(func):
        func.__doc__ = ref_func.__doc__
        return func

    return decorator


def notimplemented(func):
    '''
    Decorator function for abstract methods that are not implemented in the
    derived class.

    Raises
    ------
    NotImplementedError
        when decorated function (method) is called
    '''
    func.__doc__ = 'Not implemented.'

    def wrapper(obj, *args, **kwargs):
        raise NotImplementedError(
            'Abstract method "%s" is not implemented for derived class "%s".'
            % (func.__name__, obj.__class__.__name__))

    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


# class set_default(object):

#     '''
#     Decorator class for methods of :py:class:`tmlib.args.Args`.
#     '''

#     def __init__(self, type=None, help=None, default=None):
#         '''
#         Parameters
#         ----------
#         type: type
#             the type that the argument should have
#         help: str
#             help message that gives specifics about the argument
#         default:
#             default value for the argument

#         Raises
#         ------
#         TypeError
#         '''
#         self.type = type
#         self.help = help
#         self.default = default
#         if self.default is None:
#             self.required = True
#         else:
#             self.required = False

#     def __call__(self, obj):
#         attr_name = '_%s' % obj.__name__

#         def getter(cls):
#             if not hasattr(cls, attr_name):
#                 if self.default is None:
#                     raise ValueError(
#                             'Argument "%s" is required.' % obj.__name__)
#                 setattr(cls, attr_name, self.default)
#             setattr(cls, '%s_type' % attr_name, self.type)
#             setattr(cls, '%s_help' % attr_name, self.help)
#             return obj(cls)
#         getter.__name__ = obj.__name__
#         getter.__doc__ = obj.__doc__

#         return property(getter)

