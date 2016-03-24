'''`TissueMAPS` workflow.
'''
import importlib

from workflow import WorkflowStep
from workflow import WorkflowStage
from workflow import ParallelWorkflowStage
from workflow import SequentialWorkflowStage
from workflow import Workflow


def load_method_args(method_name):
    '''
    Load general arguments that can be parsed to a method of
    an implemented subclass of a :py:class:`tmlib.cli.CommandLineInterface`
    base class

    Parameters
    ----------
    method_name: str
        name of the method

    Returns
    -------
    tmlib.args.Args
        argument container

    Raises
    ------
    AttributeError
        when the "args" module doesn't contain a method-specific
        implementation of the `Args` base class
    '''
    module_name = '%s.args' % __name__
    module = importlib.import_module(module_name)
    try:
        class_name = '%sArgs' % method_name.capitalize()
    except ImportError:
        raise AttributeError('Method "%s" is not available.')
    return getattr(module, class_name)


def load_var_method_args(step_name, method_name):
    '''
    Load variable step-specific arguments that can be parsed to
    a method of an implemented subclass of a
    :py:class:`tmlib.cli.CommandLineInterface` base class.

    Parameters
    ----------
    step_name: str
        name of the program
    method_name: str
        name of the method

    Returns
    -------
    tmlib.args.Args
        argument container

    Note
    ----
    Returns ``None`` when the "args" module in the subpackage with name
    `step_name` doesn't contain a program- and method-specific implementation
    of the `Args` base class.

    Raises
    ------
    ImportError
        when subpackage with name `step_name`
        doesn't have a module named "args"
    '''
    package_name = '%s.%s' % (__name__, step_name)
    module_name = '%s.args' % package_name
    # importlib.import_module(package_name)
    module = importlib.import_module(module_name)
    class_name = '%s%sArgs' % (step_name.capitalize(),
                               method_name.capitalize())
    try:
        return getattr(module, class_name)
    except AttributeError:
        return None

