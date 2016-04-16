import re
import types
import logging
from abc import ABCMeta

from tmlib.utils import assert_type

logger = logging.getLogger(__name__)


class Argument(object):

    '''Descriptor class for an argument.'''

    @assert_type(
        type='type', help='basestring',
        choices=['set', 'list', 'types.NoneType'],
        flag=['basestring', 'types.NoneType']
    )
    def __init__(self, type, help, default=None, choices=None, flag=None,
            required=False):
        '''
        Parameters
        ----------
        type: type
            type of the argument
        help: str
            help message that describes the argument 
        default: , optional
            default value (default: ``None``)
        choices: set or list, optional
            set of choices for value (default: ``None``)
        flag: str, optional
            single letter that serves as a flag for command line usage
            (default: ``None``)
        required: bool, optional
            whether the argument is required (default: ``False``)

        Note
        ----
        Automatically adds a docstring in NumPy style to the instance based on 
        the values of `type` and `help`.

        Warning
        -------
        Value of `flag` must be unique within an argument collection,
        otherwise this will lead to conflicts in parsing of the arguments.
        '''
        self.type = type
        self.help = help
        if default is not None:
            if not isinstance(default, self.type):
                raise TypeError(
                    'Argument "default" must have type %s' % self.type.__name__
                )
        self.default = default
        self.choices = choices
        if self.choices is not None:
            self.choices = set(choices)
        self.flag = flag
        self.required = required
        formatted_help_message = self.help.replace('\n', ' ').split(' ')
        formatted_help_message[0] = formatted_help_message[0].lower()
        formatted_help_message = ' '.join(formatted_help_message)
        self.__doc__ = '%s: %s' % (self.type.__name__, formatted_help_message)

    @property
    def name(self):
        '''str: name of the argument'''
        return self._name

    @name.setter
    def name(self, value):
        if not isinstance(value, str):
            raise TypeError('Attribute "name" must have type str.')
        if re.search(r'[^a-z_]', value):
            raise ValueError(
                'Attribute "name" must be lower case and only contain letters '
                '(a-z) or underscores (_).'
            )
        self._name = value

    @property
    def _attr_name(self):
        return '_%s' % self.name

    def __get__(self, instance, owner):
        # Allow only instances of a class to get the value, i.e.
        # when accessed as an instance attribute, but return
        # the instance of the Argument class if accessed
        # as a class attribute
        if instance is None:
            return self
        logger.debug(
            'get argument "%s" from attribute "%s" of instance of class "%s"',
            self.name, self._attr_name, instance.__class__.__name__
        )
        if not hasattr(instance, self._attr_name):
            if self.required:
                raise AttributeError(
                    'Argument "%s" is required.' % self.name
                )
            setattr(instance, self._attr_name, self.default)
        return getattr(instance, self._attr_name)

    def __set__(self, instance, value):
        logger.debug(
            'set argument "%s" as attribute "%s" of instance of class "%s"',
            self.name, self._attr_name, instance.__class__.__name__
        )
        if not isinstance(value, self.type) and value is not None:
            raise TypeError(
                'Argument "%s" must have type %s.'
                % (self.name, self.type.__name__)
            )
        setattr(instance, self._attr_name, value)

    def add_to_argparser(self, parser):
        '''Adds the argument to an argument parser for use in a command line
        interface.

        Parameters
        ----------
        parser: argparse.ArgumentParser
            argument parser

        Returns
        -------
        argparse.ArgumentParser
            `parser` with added arguments
        '''
        flags = ['--%s' % self.name]
        kwargs = dict()
        if self.flag is not None:
            flags.append('-%s' % self.flag)
        kwargs['help'] = re.sub(r'\s+', ' ', self.help).strip()
        if self.type == bool:
            if self.default:
                kwargs['action'] = 'store_false'
            else:
                kwargs['action'] = 'store_true'
        else:
            kwargs['type'] = self.type
            kwargs['default'] = self.default
            kwargs['choices'] = self.choices
            if self.default is not None:
                kwargs['help'] += ' (default: %s)' % self.default
        kwargs['required'] = self.required
        parser.add_argument(*flags, **kwargs)


class ArgumentMeta(ABCMeta):

    '''Metaclass for adding class attributes of type
    :py:class:`tmlib.workflow.args.Argument` as descriptors to instances of
    the class.
    '''

    def __init__(cls, clsname, bases, attrs):
        super(ArgumentMeta, cls).__init__(clsname, bases, attrs)
        for name, value in attrs.iteritems():
            if isinstance(value, Argument):
                argument = value
                argument.name = name

    def __call__(cls, *args, **kwargs):
        logger.debug(
            'pass arguments to constructor of class "%s"', cls.__name__
        )
        return ABCMeta.__call__(cls, *args, **kwargs)


class ArgumentCollection(object):

    '''Abstract base class for an argument collection. The collection serves
    as a container for arguments that can be parsed to methods of 
    :py:class:`tmlib.workflow.cli.CommandLineInterface`.

    Implementations of the class can be instantiated without having to
    implement a constructor, i.e. an `__init__` method. The constructor
    accepts keyword arguments and strips the values from those arguments
    that are implemented as class attributes with type
    :py:class:`tmlib.workflow.args.Argument` and replaces any default values.
    When there is no default value specified, the argument has to be provided
    as a key-value pair. Derived classes can explicitly implement a constructor
    if required.
    '''

    __metaclass__ = ArgumentMeta

    def __init__(self, **kwargs):
        '''
        Parameters
        ----------
        **kwargs: dict, optional
            keyword arguments to overwrite
        '''
        for name, value in vars(self.__class__).iteritems():
            if isinstance(value, Argument):
                if name in kwargs:
                    setattr(self, name, kwargs[name])

    @property
    def help(self):
        '''str: brief description of the collection or the method to which
        the arguments should be passed
        '''
        return self._help

    @help.setter
    def help(self, value):
        if not isinstance(value, basestring):
            raise TypeError('Attribute "help" must have type basestring.')
        self._help = value

    @property
    def docstring(self):
        '''str: docstring in NumPy style for the method to which the arguments
        should be passed; build based on the value of the `help` attribute
        and those of the `type` and `help` attributes of individual arguments
        '''
        formatted_help_message = self.help.replace('\n', ' ').split()
        formatted_help_message[0] = formatted_help_message[0].capitalize()
        formatted_help_message = ' '.join(formatted_help_message)
        formatted_help_message += '.'
        docstring = '%s\n\nParameters\n----------\n' % formatted_help_message
        for name in dir(self):
            if name.startswith('_'):
                continue
            value = getattr(self.__class__, name)
            if isinstance(value, Argument):
                docstring += '%s: %s' % (name, value.type.__name__)
                if value.default is not None:
                    docstring += ', optional\n'
                else:
                    docstring += '\n'
                docstring += '    %s' % value.help
                if value.default is not None:
                    docstring += ' (default: ``%r``)\n' % value.default
                else:
                    docstring += '\n'

    @classmethod
    def iterargs(cls):
        '''Iterates over the class attributes of type
        :py:class:`tmlib.workflow.arg.Argument`
        '''
        for name in dir(cls):
            if name.startswith('_'):
                continue
            value = getattr(cls, name)
            if isinstance(value, Argument):
                yield value

    def iterargitems(self):
        '''Iterates over the argument items stored as attributes of the
        instance.
        '''
        for name in dir(self):
            if name.startswith('_'):
                continue
            value = getattr(self.__class__, name)
            if isinstance(value, Argument):
                yield (name, getattr(self, name))

    def add_to_argparser(self, parser):
        '''Adds each argument to an argument parser for use in a command line
        interface.

        Parameters
        ----------
        parser: argparse.ArgumentParser
            argument parser

        Returns
        -------
        argparse.ArgumentParser
            `parser` with added arguments
        '''
        for name in dir(self):
            if name.startswith('__'):
                continue
            value = getattr(self.__class__, name)
            if isinstance(value, Argument):
                value.add_to_argparser(parser)
        return parser

    def as_list(self):
        '''Returns class attributes of type
        :py:class:`tmlib.workflow.args.Argument` as an array of key-value pairs.

        Returns
        -------
        List[dict]
            description of each argument
        '''
        description = list()
        for arg in self.iterargs():
            argument = {
                'name': arg.name,
                'help': re.sub(r'\s+', ' ', arg.help).strip(),
                'default': arg.default,
                'type': arg.type
            }
            if arg.choices is not None:
               argument['choices'] = list(arg.choices)
            else:
                argument['choices'] = None
            description.append(argument)
        return description

    @assert_type(collection='tmlib.workflow.args.ArgumentCollection')
    def union(self, collection):
        '''Adds all arguments contained in another `collection`.

        Parameters
        ----------
        collection: tmlib.workflow.args.ArgumentCollection
            collection of arguments that should be added
        '''
        for name in dir(collection):
            if name.startswith('__'):
                continue
            value = getattr(self.__class__, name)
            if isinstance(value, Argument):
                setattr(self.__class__, name, value)


class BatchArguments(ArgumentCollection):

    '''Base class for arguments that are used to define how the
    computational task should be devided into individual batch jobs
    for parallel processing on the cluster.

    These arguments can be passed to a step-specific implementation of
    :py:method:`tmlib.workflow.cli.CommandLineInterface.init` and are
    required by :py:method:`tmlib.workflow.api.ClusterRoutines.create_batches`.

    Note
    ----
    Each workflow step must implement this class and add the arguments that
    the user should be able to set.
    '''


class SubmissionArguments(ArgumentCollection):

    '''Base class for arguments that are used to control the submission of
    jobs to the cluster.

    These arguments can be passed to a step-specific implementation of
    :py:method:`tmlib.workflow.cli.CommandLineInterface.submit` and are
    required by :py:method:`tmlib.workflow.api.ClusterRoutines.create_jobs`.

    Note
    ----
    Each workflow step must implement this class and potentially override
    the provided defaults depending on the requirements of the jobs.

    '''

    duration = Argument(
        type=str, default='02:00:00',
        help='''
            walltime that should be allocated to a each "run" job
            in the format "HH:MM:SS"
        '''
    )

    memory = Argument(
        type=int, default=3800,
        help='''
            amount of memory that should be allocated to each "run" job
            in megabytes (MB)
        '''
    )

    cores = Argument(
        type=int, default=1,
        help='''
            number of cores that should be allocated to each "run" job
        '''
    )


class ExtraArguments(ArgumentCollection):

    '''Collection of arguments that can be passed to the constructor of
    API classes, i.e. a step-specific implementation of
    :py:class:`tmlib.workflow.api.ClusterRoutines`, in addition to the default
    arguments `experiment_id` and `verbosity`.

    Note
    ----
    A step may implement this class if required.
    '''


class CliMethodArguments(ArgumentCollection):

    '''Collection of arguments that can be passed to a method of
    a step-specific implemenation of
    :py:class:`tmlib.workflow.cli.CommandLineInterface`.

    Note
    ----
    This class is automatically implemented for each method by the
    :py:function:`tmlib.workflow.registry.climethod` decorator.
    '''


# class argument_property(object):

#     '''Custom implementation of `property` that allows setting additional
#     attributes on the object. It can be used to represent a command line
#     argument and to add it to an instance of :py:class:`argparse.ArgumentParser`.
#     '''

#     def __init__(self, getter, setter):
#         '''
#         Parameters
#         ----------
#         getter: function
#             getter function for returning the value
#         setter: function
#             setter function that accepts the value as an argument
#         '''
#         self.getter = getter
#         self.setter = setter

#     def __get__(self, instance, owner):
#         return self.getter(instance)

#     def __set__(self, instance, value):
#         self.setter(instance, value)


# class add_argument(object):

#     '''Decorator class that acts like a property.
#     The value represents an argument that can be parsed via the command line.

#     The setter of the property checks whether the value has the specified
#     `type` and whether it is in the set of valid `choices` (if provided).
#     The getter return the `default` value if provided and if it has not been
#     overwritten, i.e. a different value has been set.
    
#     Raises
#     ------
#     TypeError
#         when type of the property value doesn't have the specified `type`
#     ValueError
#         when the property value is not one the specified `choices`
    
#     Note
#     ----
#     Values of type ``basestring`` (e.g. ``unicode``) are converted to ``str``
#     before `type` is checked, so use ``type=str`` for all strings.

#     Examples
#     --------
#     from tmlib.utils import argument_parserargument_property
    
#     class Foo(object):

#         @add_argument(
#             type=int, help='help for bar', default=1, choices={1, 2}
#         )
#         def bar(self:
#             return self._bar

#     >>>foo = Foo()
#     >>>foo.bar
#     1
#     >>>foo.bar = 2
#     >>>foo.bar
#     2
#     >>>foo.bar = 3
#     ValueError: Argument "bar" can be one of the following: 1, 2
#     >>>foo.bar = 1.0
#     TypeError: Argument "bar" must have type int.
#     '''

#     @assert_type(
#         type='type', help='basestring', choices=['set', 'types.NoneType'],
#         flag=['basestring', 'types.NoneType']
#     )
#     def __init__(self, type, help, default=None, choices=None, flag=None):
#         '''
#         Parameters
#         ----------
#         type: type
#             type of the argument
#         help: str
#             help message that describes the argument 
#         default: , optional
#             default value
#         choices: set, optional
#             set of choices for value
#         flag: str, optional
#             short name for a command line (will be prepended with a hyphen)
#         '''
#         self.type = type
#         self.help = help
#         if default is not None:
#             if not isinstance(default, self.type):
#                 raise TypeError(
#                     'Argument "default" must have type %s' % self.type.__name__
#                 )
#         self.default = default
#         self.choices = choices
#         self.flag = flag

#     def __call__(self, obj):
#         attr_name = '_%s' % obj.__name__

#         def getter(cls):
#             if not hasattr(cls, attr_name):
#                 if self.default is None:
#                     raise ValueError(
#                         'Argument "%s" is required.' % obj.__name__
#                     )
#                 setattr(cls, attr_name, self.default)
#             return obj(cls)
#         getter.__name__ = obj.__name__
#         # NOTE: The docstring for the getter is automatically build using the
#         # provided type and help attributes.
#         getter.__doc__ = '{type}: {description}'.format(
#             type=self.type.__name__, description=self.help
#         )

#         def setter(cls, value):
#             if isinstance(value, basestring):
#                 value = str(value)
#             if not isinstance(value, self.type):
#                 raise TypeError(
#                     'Argument "%s" must have type %s.'
#                     % (obj.__name__, self.type.__name__)
#                 )
#             if self.choices is not None:
#                 if value not in self.choices:
#                     raise ValueError(
#                         'Argument "%s" must be one of the following: %s'
#                         % (obj.__name__,
#                            ', '.join(['%r' % c for c in self.choices]))
#                     )
#             setattr(cls, attr_name, value)

#         property_obj = argument_property(getter, setter)
#         property_obj.type = self.type
#         property_obj.help = self.help
#         property_obj.choices = self.choices
#         property_obj.flag = self.flag
#         return property_obj
