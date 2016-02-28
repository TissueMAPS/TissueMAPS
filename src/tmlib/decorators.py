import inspect
import functools
import types
from types import *


def assert_type(**expected_types):
    '''
    Function decorator that checks that type of the function arguments.

    Parameters
    ----------
    expected_types: Dict[str, type or Set[type]], optional
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
    class Test(object):

        @assert_type(value1=str, value2={int, float, types.NoneType})
        def print_args(value1, value2=None):
            print 'value1: "%s"' % value1
            if value2:
                print 'value2: %d' % value2
    '''
    def decorator(func):

        @functools.wraps(func)
        def wrapper(obj, *args):

            inputs = inspect.getargspec(func)
            for name, expected_type in expected_types.iteritems():
                if name not in inputs.args:
                    raise ValueError('Unknown argument "%s"' % name)
                index = inputs.args.index(name)
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
                                    (name, options))
            return func(*args)

        wrapper.func_name = func.func_name
        return wrapper

    return decorator

