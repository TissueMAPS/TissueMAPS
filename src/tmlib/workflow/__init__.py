'''A  `workflow` is a sequence of computational tasks
that should be processed on a cluster computer.
It is composed of one or more `stages`, which are themselves composed of one
or more `steps`. A `step` represents a collection of batch jobs that
should be processed in parallel. A `stage` bundles mutliple `steps` into a
logical processing unit taking potential dependencies between `steps` into
account.

Each `step` represents a subpackage, which must implement the following
modules:

    * **api**: must implement :class:`tmlib.workflow.api.ClusterRoutines`
    and decorate it with :function:`tmlib.workflow.registry.api`
    * **args**: must implement :class`tmlib.workflow.args.BatchArguments` and
    :class:`tmlib.workflow.args.SubmissionArguments` and decorate them with
    :function:`tmlib.workflow.registry.batch_args` and
    :function:`tmlib.workflow.registry.submission_args`, respectively
    * **cli**: must implement :class:`tmlib.workflow.cli.CommandLineInterface`

This automatically registers each step and enables using it via the
command line and/or integrating it into a workflow.
'''
import os
import glob

import logging
import inspect
import importlib
import types
import collections

from tmlib import __version__

logger = logging.getLogger(__name__)


_step_register = collections.defaultdict(dict)
_workflow_register = collections.defaultdict(dict)


def register_api(step_name):
    '''Class decorator to register a derived class of
    :class:`tmlib.workflow.api.ClusterRoutines` as an API for use in
    command line interface and workflow.

    Parameters
    ----------
    step_name: str
        name of the corresponding worklow step

    Returns
    -------
    tmlib.workflow.args.ClusterRoutines

    Raises
    ------
    TypeError
        when decorated class is not derived from
        :class:`tmlib.workflow.api.ClusterRoutines`
    '''
    from tmlib.workflow.api import ClusterRoutines
    def decorator(cls):
        if ClusterRoutines not in inspect.getmro(cls):
            raise TypeError(
                'Api class must be derived from '
                '"tmlib.workflow.api.ClusterRoutines"'
            )
        _step_register[step_name]['api'] = cls
        return cls
    return decorator


def register_workflow_type(name):
    '''Class decorator to register a derived class of
    :class:`tmlib.workflow.description.WorkflowDependencies` for use in
    command line interface and workflow.

    Parameters
    ----------
    name: str
        name of the type of workflow

    Returns
    -------
    tmlib.workflow.description.WorkflowDependencies

    Raises
    ------
    TypeError
        when decorated class is not derived from
        :class:`tmlib.workflow.dependencies.WorkflowDependencies`
    '''
    from tmlib.workflow.dependencies import WorkflowDependencies
    def decorator(cls):
        if WorkflowDependencies not in inspect.getmro(cls):
            raise TypeError(
                'Registered class must be derived from '
                '"tmlib.workflow.dependencies.WorkflowDependencies"'
            )
        cls.type = name
        _workflow_register[name] = cls
        return cls
    return decorator


def climethod(help, **kwargs):
    '''Method decorator that flags a method for use in the command line
    interface and provides description for the arguments of the method, which
    are required for parsing of arguments via the command line.

    Parameters
    ----------
    help: str
        brief description of the method
    **kwargs: Dict[str, tmlib.workflow.args.Argument]
        descriptors for each argument of the method

    Returns
    -------
    unboundmethod

    Raises
    ------
    TypeError
        when registered function is not a method
    TypeError
        when the class of the registered method is not derived from
        :class:`tmlib.workflow.cli.CommandLineInterface`
    TypeError
        when the value specified by a keyword argument doesn't have type
        :class:`tmlib.workflow.args.Argument`
    ValueError
        when the key of an keyword argument doesn't match a parameter
        of the method
    '''
    from tmlib.workflow.args import Argument
    from tmlib.workflow.args import CliMethodArguments
    from tmlib.workflow.args import ArgumentMeta
    def decorator(func):
        if not isinstance(func, types.FunctionType):
            raise TypeError('Registered object must be a function.')
        # if CommandLineInterface not in inspect.getmro(func.im_class):
        #     raise TypeError(
        #         'Class of registered method must be derived from '
        #         'tmlib.workflow.cli.CommandLineInterface'
        #     )
        func.is_climethod = True
        func.help = help
        func.args = ArgumentMeta(
            '%sCliMethodArguments' % func.__name__.capitalize(),
            (CliMethodArguments,), dict()
        )
        # The first argument of a method is the class instance
        argument_names = inspect.getargspec(func).args[1:]
        for name in argument_names:
            if name not in kwargs:
                raise ValueError(
                    'Argument "%s" unspecified for CLI method "%s".'
                    % (name, func.__name__)
                )
        for name, value in kwargs.iteritems():
            if name not in argument_names:
                raise ValueError(
                    'Argument "%s" is not a valid argument for CLI method "%s"'
                    % (name, func.__name__)
                )
            if not isinstance(value, Argument):
                raise TypeError(
                    'The value specified by keyword argument "%s" must have '
                    'type tmlib.workflow.args.Argument' % name
                )
            value.name = name
            setattr(func.args, name, value)
        return func
    return decorator


def register_batch_args(step_name):
    '''Class decorator to register a derived class of
    :class:`tmlib.workflow.args.BatchArguments` for a workflow
    step to use it via the command line or within a workflow.

    Parameters
    ----------
    step_name: str
        name of the corresponding workflow step

    Returns
    -------
    tmlib.workflow.args.BatchArguments

    Raises
    ------
    TypeError
        when decorated class is not derived from
        :class:`tmlib.workflow.args.BatchArguments`
    '''
    from tmlib.workflow.args import BatchArguments
    def decorator(cls):
        if BatchArguments not in inspect.getmro(cls):
            raise TypeError(
                'Registered class must be derived from '
                'tmlib.workflow.args.BatchArguments'
            )
        _step_register[step_name]['batch_args'] = cls
        return cls
    return decorator


def register_submission_args(step_name):
    '''Class decorator to register a derived class of
    :class:`tmlib.workflow.args.SubmissionArguments` for a worklow
    step to use it via the command line or within a worklow.

    Parameters
    ----------
    step_name: str
        name of the corresponding workflow step

    Returns
    -------
    tmlib.workflow.args.SubmissionArguments

    Raises
    ------
    TypeError
        when decorated class is not derived from
        :class:`tmlib.workflow.args.SubmissionArguments`
    '''
    from tmlib.workflow.args import SubmissionArguments
    def decorator(cls):
        if SubmissionArguments not in inspect.getmro(cls):
            raise TypeError(
                'Registered class must be derived from '
                'tmlib.workflow.args.SubmissionArguments'
            )
        _step_register[step_name]['submission_args'] = cls
        return cls
    return decorator


def register_extra_args(step_name):
    '''Class decorator to register a derived class of
    :class:`tmlib.workflow.args.ExtraArguments` for a worklow
    step to use it via the command line or within a worklow.

    Parameters
    ----------
    step_name: str
        name of the corresponding workflow step

    Returns
    -------
    tmlib.workflow.args.ExtraArguments

    Raises
    ------
    TypeError
        when decorated class is not derived from
        :class:`tmlib.workflow.args.ExtraArguments`
    '''
    from tmlib.workflow.args import ExtraArguments
    def decorator(cls):
        if ExtraArguments not in inspect.getmro(cls):
            raise TypeError(
                'Registered class must be derived from '
                'tmlib.workflow.args.ExtraArguments'
            )
        _step_register[step_name]['extra_args'] = cls
        return cls
    return decorator


def get_step_args(name):
    '''Gets the step-specific implementations of the argument collection
    classes.

    Parameters
    ----------
    name: str
        name of the step

    Returns
    -------
    Tuple[tmlib.workflow.args.ArgumentCollection or None]
        batch and submission arguments and extra arguments in case the step
        implemented any
    '''
    module_name = '%s.%s.args' % (__name__, name)
    try:
        module = importlib.import_module(module_name)
    except ImportError as error:
        raise ValueError(
            'Import of module "%s" failed: %s' % (module_name, str(error))
        )
    # Once the module has been loaded, the argument collection classes
    # are available in the register
    batch_args = _step_register[name]['batch_args']
    submission_args = _step_register[name]['submission_args']
    extra_args = _step_register[name].get('extra_args', None)
    return (batch_args, submission_args, extra_args)


def get_step_api(name):
    '''Gets the step-specific implementation of the API class.

    Parameters
    ----------
    name: str
        name of the step

    Returns
    -------
    tmlib.workflow.api.ClusterRoutines
        api class
    '''
    module_name = '%s.%s.api' % (__name__, name)
    try:
        module = importlib.import_module(module_name)
    except ImportError as error:
        raise ImportError(
            'Import of module "%s" failed: %s' % (module_name, str(error))
        )
    except:
        raise
    return _step_register[name]['api']


def get_step_information(name):
    '''Gets the full name of the given step and a brief description.

    Parameters
    ----------
    name: str
        name of the step

    Returns
    -------
    Tuple[str]
        full name and brief description
    '''
    subpkg_name = '%s.%s' % (__name__, name)
    try:
        subpkg = importlib.import_module(subpkg_name)
    except ImportError as error:
        raise ImportError(
            'Import of package "%s" failed: %s' % (subpkg_name, str(error))
        )
    except:
        raise
    return (subpkg.__fullname__, subpkg.__description__)


def get_workflow_dependencies(name):
    '''Gets an implementation of a workflow dependency declaration.

    Parameters
    ----------
    name: str
        name of a workflow type

    Returns
    -------
    tmlib.workflow.description.WorkflowDependencies
    '''
    module_name = '%s.%s' % (__name__, name)
    try:
        module = importlib.import_module(module_name)
    except ImportError as error:
        raise ImportError(
            'Import of module "%s" failed: %s' % (module_name, str(error))
        )
    return _workflow_register[name]


from workflow import Workflow
from workflow import WorkflowStep
from workflow import ParallelWorkflowStage
from workflow import SequentialWorkflowStage


