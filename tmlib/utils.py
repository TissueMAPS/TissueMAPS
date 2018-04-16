# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
# Copyright (C) 2018  University of Zurich
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''Decorators and other utility functions.'''
import importlib
import itertools
import time
import datetime
import re
import os
import inspect
from decorator import decorator
from types import *
import logging

logger = logging.getLogger(__name__)


def create_partitions(li, n):
    '''Creates a list of sublists from a list, where each sublist has length n.

    Parameters
    ----------
    li: list
        list that should be partitioned
    n: int
        number of items per sublist

    Returns
    -------
    List[list]
    '''
    n = max(1, n)
    return [li[i:i + n] for i in range(0, len(li), n)]


def create_datetimestamp():
    '''Creates a datetimestamp in the form "year-month-day_hour-minute-second".

    Returns
    -------
    str
        datetimestamp
    '''
    t = time.time()
    return datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d_%H-%M-%S')


def create_timestamp():
    '''Creates a timestamp in the form "hour-minute-second".

    Returns
    -------
    str
        timestamp
    '''
    t = time.time()
    return datetime.datetime.fromtimestamp(t).strftime('%H-%M-%S')


def create_directory(location):
    '''Creates a directory on disk in a safe way.

    Parameters
    ----------
    location: str
        absolute path to the directory that should be created
    '''
    try:
        os.makedirs(location)
    except OSError as err:
        if err.errno != 17:
            raise
        pass


def regex_from_format_string(format_string):
    '''Converts a format string with keywords into a named regular expression.

    Parameters
    ----------
    format_string: str
        Python format string

    Returns
    -------
    _sre.SRE_Pattern
        compiled named regular expression pattern

    Examples
    --------
    >>> r = regex_from_format_string("{directory}/{filename}")
    >>> r.search("foo/bar.txt").groupdict()
    {'directory': 'foo', 'filename': 'bar.txt'}
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
        regex = re.sub(pl_regex, '(?P<%s>.*)' % pl_name, regex)

    return re.compile(regex)


def indices(data, item):
    '''Determines all indices of an item in a list.

    Parameters
    ----------
    data: list
    item:
        the element whose index positions should be determined

    Returns
    -------
    List[int]
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
    '''Transforms a list of lists into a flat list.

    Parameters
    ----------
    data: List[list]

    Returns
    -------
    list
    '''
    return list(itertools.chain.from_iterable(data))
    # return [item for sublist in data for item in sublist]


def common_substring(data):
    '''Finds longest common substring across a collection of strings.

    Parameters
    ----------
    data: List[str]

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
    '''Captures the whole directory tree downstream of `start_dir`.

    Parameters
    ----------
    start_dir: str
        absolute path to the directory whose content should be listed
    '''
    for root, dirs, files in os.walk(start_dir):
        level = root.replace(start_dir, '').count(os.sep)
        indent = ' ' * 4 * (level)
        logger.info('{}{}/'.format(indent, os.path.basename(root)))


def is_number(s):
    '''Checks whether a string can be represented by a number.

    Parameters
    ----------
    s: str

    Returns
    -------
    bool

    Examples
    --------
    >>> is_number('blabla')
    False
    >>> is_number('007')
    True
    '''
    # NOTE: code taken from stackoverflow.com (question 354038)
    try:
        float(s)
        return True
    except ValueError:
        return False


def map_letter_to_number(letter):
    '''Maps capital letter to number.

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
    >>> map_letter_to_number("A")
    1
    '''
    return ord(letter) - 64


def map_number_to_letter(number):
    '''Maps number to capital letter.

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
    >>> map_number_to_letter(1)
    "A"
    '''
    return chr(number+64)


def missing_elements(data, start=None, end=None):
    '''Determines missing elements in a sequence of integers.

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
    >>> data = [10, 12, 13, 15, 16, 19, 20]
    >>> list(missing_elements(data))
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
    '''Decorator function that asserts that the type of function arguments.

    Parameters
    ----------
    expected: Dict[str, str or List[str]], optional
        key-value pairs of names and expected types
        of each argument that should be checked

    Raises
    ------
    ValueError
        when a name is provided that is not an argument of the function
    TypeError
        when type of the function argument doesn't match the expected type or
        when `expected` is not provided in the correct type

    Note
    ----
    Custom types will by dynamically imported. To this end, they have to be
    provided with the full name, i.e. including package and module names.
    The same is true for special built-in types, such as `types.NoneType`.

    Examples
    --------
    .. code:: python

        from tmlib.utils import assert_type

        class TypeCheckExample(object):

            @assert_type(value1='str', value2=['int', 'float', 'types.NoneType'])
            def test(self, value1, value2=None):
                print 'value1: "%s"' % value1
                if value2:
                    print 'value2: %d' % value2

        example = TypeCheckExample()
        example.test('blabla', 2)
        example.test('blabla', 2.0)
        example.test('blabla', None)
        example.test('blabla')
        example.test('blabla', '2')  # raises TypeError

    '''

    @decorator
    def wrapper(func, *args, **kwargs):
        inputs = inspect.getargspec(func)
        for expected_name, expected_type in expected.iteritems():
            if expected_name not in inputs.args:
                raise ValueError('Unknown argument "%s"' % expected_name)
            index = inputs.args.index(expected_name)
            if index >= len(args):
                continue
            if isinstance(expected_type, str):
                et_strings = [expected_type]
            elif isinstance(expected_type, list):
                et_strings = expected_type
            else:
                raise TypeError(
                    'Expected types for function "%s" have to provided as '
                    'either a string of a list of strings.'
                    % func.__name__
                )

            # Users provide the types as strings. The advantage is that
            # the corresponding object doesn't have to be imported by the
            # user. But we have to convert the strings into types and
            # import custom type objects in order to be able to check their
            # type.
            et_types = list()
            for ets in et_strings:
                try:
                    # First, let's deal with built-in types
                    ett = eval(ets)
                except NameError:
                    try:
                        # It's not a built-in type. So we may deal with a
                        # custom type.
                        # Let's import the corresponding module and get
                        # the object for which we want to check the type.
                        path_parts = ets.split('.')
                        fullname = '.'.join(path_parts[:-1])
                        module = importlib.import_module(fullname)
                        try:
                            ett = getattr(module, path_parts[-1])
                        except AttributeError:
                            raise AttributeError(
                                'Custom type %s does not exist.' % fullname
                            )
                    except ImportError:
                        raise ImportError(
                            'Import of custom type "%s" failed.' % ets
                        )
                if not isinstance(ett, type):
                    raise TypeError(
                        'Type of "%s" could not be determined' % ett
                    )
                et_types.append(ett)

            # No we have a type object that we can use for the check
            if not any([isinstance(args[index], ett) for ett in et_types]):
                options = ' or '.join([ets for ets in et_strings])
                raise TypeError(
                    'Argument "%s" must have type %s.'
                    % (expected_name, options)
                )
        return func(*args, **kwargs)

    return wrapper


def assert_path_exists(*expected):
    '''Decorator function that asserts that a path to a file or directory on
    disk specified by a function argument exists.

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
    '''
    @decorator
    def wrapper(func, *args, **kwargs):
        inputs = inspect.getargspec(func)
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

    return wrapper


class autocreate_directory_property(object):

    '''Decorator class that acts like a property.
    The value represents a path to a directory on disk. The directory is
    automatically created when it doesn't exist. Once created, the value
    is cached, so that there is no reattempt to create the directory.

    Raises
    ------
    TypeError
        when the value of the property doesn't have type basestring
    ValueError
        when the value of the property is empty

    Examples
    --------
    .. code:: python

        from tmlib.utils import autocreate_directory_property

        class Foo(object):

            @autocreate_directory_property
            def my_new_directory(self):
                return '/tmp/blabla'

        foo = Foo()
        foo.my_new_directory
    '''
    def __init__(self, func):
        self.__doc__ = func.__doc__
        self.func = func

    def __get__(self, obj, cls):
        if obj is None:
            return self
        value = obj.__dict__[self.func.__name__] = self.func(obj)
        if not isinstance(value, basestring):
            raise TypeError(
                'Value of property "%s" must have type basestring: %s'
                % (self.func.__name__, value)
            )
        if not value:
            raise ValueError(
                'Value of property "%s" cannot be empty.'
                % self.func.__name__
            )
        if not os.path.exists(value):
            logger.debug('create directory: %s', value)
            create_directory(value)
        return value


def same_docstring_as(ref_func):
    '''Decorator function that sets the docstring of the decorate function
    to the one of `ref_func`.
    This is helpful for methods of derived classes that should "inherit"
    the docstring of the abstract method in the base class.

    Parameters
    ----------
    ref_func: function
        reference function from which the docstring should be copied
    '''

    def wrapper(func):
        func.__doc__ = ref_func.__doc__
        return func

    return wrapper


def notimplemented(func):
    '''Decorator function for abstract methods that are not implemented in the
    derived class.

    Raises
    ------
    NotImplementedError
        when decorated function (method) is called

    Note
    ----
    Derived classes of
    :class:`WorkflowStepAPI <tmlib.workflow.api.WorkflowStepAPI>`
    must decorate the implemented method `collect_job_output` in case the
    corresponding step doesn't have a `collect` phase.
    '''
    func.__doc__ = 'Not implemented.'

    def wrapper(obj, *args, **kwargs):
        raise NotImplementedError(
            'Abstract method "%s" is not implemented for derived class "%s".'
            % (func.__name__, obj.__class__.__name__)
        )

    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    # NOTE: this is used by tmlib.workflow.cli._CliMeta!
    wrapper.is_climethod = False
    # NOTE: this is used by tmlib.workflow.api._ApiMeta!
    wrapper.is_implemented = False
    return wrapper
