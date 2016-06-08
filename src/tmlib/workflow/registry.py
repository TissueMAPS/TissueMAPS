import logging
import inspect
import importlib
import collections

from tmlib import __version__
from tmlib.workflow.args import Argument
from tmlib.workflow.args import CliMethodArguments
from tmlib.workflow.args import ArgumentMeta

logger = logging.getLogger(__name__)


_step_register = collections.defaultdict(dict)
_workflow_register = collections.defaultdict(dict)


def api(step_name):
    '''Class decorator to register a derived class of
    :py:class:`tmlib.workflow.api.ClusterRoutines` as an API for use in
    command line interface and workflow.

    Parameters
    ----------
    step_name: str
        name of the corresponding worklow step

    Returns
    -------
    tmlib.workflow.args.ClusterRoutines
    '''
    def decorator(cls):
        _step_register[step_name]['api'] = cls
        return cls
    return decorator


def workflow(workflow_type):
    '''Class decorator to register a derived class of
    :py:class:`tmlib.workflow.description.WorkflowDependencies` for use in
    command line interface and workflow.

    Parameters
    ----------
    workflow_type: str
        name of the type of workflow

    Returns
    -------
    tmlib.workflow.description.WorkflowDependencies
    '''
    def decorator(cls):
        cls.type = workflow_type
        _workflow_register[workflow_type] = cls
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
    function
    '''
    def decorator(func):
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


def batch_args(step_name):
    '''Class decorator to register a derived class of
    :py:class:`tmlib.workflow.args.BatchArguments` for a workflow
    step to use it via the command line or within a workflow.

    Parameters
    ----------
    step_name: str
        name of the corresponding workflow step

    Returns
    -------
    tmlib.workflow.args.BatchArguments
    '''
    def decorator(cls):
        _step_register[step_name]['batch_args'] = cls
        return cls
    return decorator 


def submission_args(step_name):
    '''Class decorator to register a derived class of
    :py:class:`tmlib.workflow.args.SubmissionArguments` for a worklow
    step to use it via the command line or within a worklow.

    Parameters
    ----------
    step_name: str
        name of the corresponding workflow step

    Returns
    -------
    tmlib.workflow.args.SubmissionArguments
    '''
    def decorator(cls):
        _step_register[step_name]['submission_args'] = cls
        return cls
    return decorator


def extra_args(step_name):
    '''Class decorator to register a derived class of
    :py:class:`tmlib.workflow.args.ExtraArguments` for a worklow
    step to use it via the command line or within a worklow.

    Parameters
    ----------
    step_name: str
        name of the corresponding workflow step

    Returns
    -------
    tmlib.workflow.args.ExtraArguments
    '''
    def decorator(cls):
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
    pkg_name = '.'.join(__name__.split('.')[:-1])
    module_name = '%s.%s.args' % (pkg_name, name)
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
    pkg_name = '.'.join(__name__.split('.')[:-1])
    module_name = '%s.%s.api' % (pkg_name, name)
    try:
        module = importlib.import_module(module_name)
    except ImportError as error:
        raise ImportError(
            'Import of module "%s" failed: %s' % (module_name, str(error))
        )
    except:
        raise
    return _step_register[name]['api']


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
    pkg_name = '.'.join(__name__.split('.')[:-1])
    module_name = '%s.%s' % (pkg_name, name)
    try:
        module = importlib.import_module(module_name)
    except ImportError as error:
        raise ImportError(
            'Import of module "%s" failed: %s' % (module_name, str(error))
        )
    return _workflow_register[name]
