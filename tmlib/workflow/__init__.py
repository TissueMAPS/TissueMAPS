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
'''`TissueMAPS` workflow.

A *workflow* is a sequence of distributed computational tasks
(`steps`). Each *step* represents a collection of batch jobs that can be
processed in parallel and is comprised of the following phases:

    * **init**: Paritioning of the computational task into smaller batches
      based on user provided arguments.
    * **run**: Scheduled parallel processing of individual batches according to
      user defined resource allocation.
    * **collect** (optional): Postprocessing of results obtained by individual
      batch jobs.

A *step* is implemented as a subpackage of :mod:`tmlib.workflow` containing
three modules:

    * **args**: Must implement
      :class:`BatchArguments <tmlib.workflow.args.BatchArguments>` and
      :class:`SubmissionArguments <tmlib.workflow.args.SubmissionArguments>`
      and decorate them with
      :func:`register_step_batch_args <tmlib.workflow.register_step_batch_args>`
      and
      :func:`register_step_submission_args <tmlib.workflow.register_step_submission_args>`,
      respectively. These classes provide *step*-specific arguments controlling
      the partitioning of the given computational task into separate batch jobs
      and the amount of computational resources, which should get allocated
      to each batch job.
    * **api**: Must implement
      :class:`WorkflowStepAPI <tmlib.workflow.api.WorkflowStepAPI>` and
      decorate it with
      :func:`register_step_api <tmlib.workflow.register_step_api>`. This class
      provides the active programming interface (API) with methods for
      creation and management of batch jobs. The methods
      :meth:`create_batches <tmlib.workflow.api.WorkflowStepAPI.create_batches>`,
      :meth:`run_job <tmlib.workflow.api.WorkflowStepAPI.run_job>` and
      :meth:`collect_job_output <tmlib.workflow.api.WorkflowStepAPI.collect_job_output>`
      implemented by derived classes are responsible for the *step*-specific
      processing behaviour and controlled via the *batch* and *submission*
      arguments described above.
    * **cli**: Must implement
      :class:`WorkflowStepCLI <tmlib.workflow.cli.WorkflowStepCLI>`.
      This class provides the command line interface (CLI) and main entry points
      for the program. It supplies high-level methods for the different
      *phases*, which delegate processing to the respective API methods.

This implementation automatically registers a *step* and makes it available
for integration into larger workflows.
To this end, *steps* are further combined into abstract task collections
referred to as *stages*. A *stage* bundles one ore more *steps*
into a logical processing unit taking potential dependencies between them
into account.

A :class:`Workflow <tmlib.workflow.workflow.Workflow>` is dynamically build
from *steps* based on
:class:`WorkflowDescription <tmlib.workflow.description.WorkflowDescription>` -
provided by users as a mapping in *YAML* format.
The *workflow* structure, i.e. the sequence of *stages* and *steps* and their
interdependencies, is defined by its *type*, which is determined based on an
implementation of
:class:`WorkflowDependencies <tmlib.workflow.dependencies.WorkflowDependencies>`.
To make a *type* available for use, the derived class must be
registered via
:func:`register_workflow_type <tmlib.workflow.register_workflow_type>`.
As an example serves the "canonical" type declared by
:class:`CanonicalWorkflowDependencies <tmlib.workflow.canonical.CanonicalWorkflowDependencies>`.

'''
import os
import glob

import logging
import inspect
import importlib
import types
import collections

from tmlib import __version__
from tmlib.errors import RegistryError

logger = logging.getLogger(__name__)


_step_register = collections.defaultdict(dict)
_workflow_register = collections.defaultdict(dict)


def register_step_api(name):
    '''Class decorator to register a derived class of
    :class:`WorkflowStepAPI <tmlib.workflow.api.WorkflowStepAPI>` as a step API.

    Parameters
    ----------
    name: str
        name of the corresponding worklow step

    Returns
    -------
    classobj

    Raises
    ------
    TypeError
        when decorated class is not derived from
        :class:`WorkflowStepAPI <tmlib.workflow.api.WorkflowStepAPI>`
    '''
    from tmlib.workflow.api import WorkflowStepAPI
    def decorator(cls):
        if WorkflowStepAPI not in inspect.getmro(cls):
            raise TypeError(
                'Api class must be derived from '
                '"tmlib.workflow.api.WorkflowStepAPI"'
            )
        _step_register[name]['api'] = cls
        return cls
    return decorator


def register_workflow_type(name):
    '''Class decorator to register a derived class of
    :class:`WorkflowDependencies <tmlib.workflow.dependencies.WorkflowDependencies>`.

    Parameters
    ----------
    name: str
        name of the type of workflow

    Returns
    -------
    classobj

    Raises
    ------
    TypeError
        when decorated class is not derived from
        :class:`WorkflowDependencies <tmlib.workflow.dependencies.WorkflowDependencies>`
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

    The decorator further constructs the docstring for the docorated method.

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
        :class:`WorkflowStepCLI <tmlib.workflow.cli.WorkflowStepCLI>`
    TypeError
        when the value specified by a keyword argument doesn't have type
        :class:`Argument <tmlib.workflow.args.Argument>`
    ValueError
        when the key of an keyword argument doesn't match a parameter
        of the method
    '''
    from tmlib.workflow.args import Argument
    from tmlib.workflow.args import CliMethodArguments
    from tmlib.workflow.args import _ArgumentMeta
    def decorator(func):
        if not isinstance(func, types.FunctionType):
            raise TypeError('Registered object must be a function.')
        # if WorkflowStepCLI not in inspect.getmro(func.im_class):
        #     raise TypeError(
        #         'Class of registered method must be derived from '
        #         'tmlib.workflow.cli.WorkflowStepCLI'
        #     )
        func.is_climethod = True
        func.help = help
        func.args = _ArgumentMeta(
            '%sCliMethodArguments' % func.__name__.capitalize(),
            (CliMethodArguments,), dict()
        )
        # The first argument of a method is the class instance
        func.__doc__ = '%s\n' % help.capitalize()
        if kwargs:
            func.__doc__ += '\nParameters\n----------\n'
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
            func.__doc__ += '%s: %s\n    %s\n' % (
                name, value.type.__name__, value.help
            )
        return func
    return decorator


def register_step_batch_args(name):
    '''Class decorator to register a derived class of
    :class:`BatchArguments <tmlib.workflow.args.BatchArguments>` for a workflow
    step to use it via the command line or within a workflow.

    Parameters
    ----------
    name: str
        name of the corresponding workflow step

    Returns
    -------
    classobj

    Raises
    ------
    TypeError
        when decorated class is not derived from
        :class:`BatchArguments <tmlib.workflow.args.BatchArguments>`
    '''
    from tmlib.workflow.args import BatchArguments
    def decorator(cls):
        if BatchArguments not in inspect.getmro(cls):
            raise TypeError(
                'Registered class must be derived from '
                'tmlib.workflow.args.BatchArguments'
            )
        _step_register[name]['batch_args'] = cls
        return cls
    return decorator


def register_step_submission_args(name):
    '''Class decorator to register a derived class of
    :class:`SubmissionArguments <tmlib.workflow.args.SubmissionArguments>`
    for a worklow step to use it via the command line or within a worklow.

    Parameters
    ----------
    name: str
        name of the corresponding workflow step

    Returns
    -------
    classobj

    Raises
    ------
    TypeError
        when decorated class is not derived from
        :class:`SubmissionArguments <tmlib.workflow.args.SubmissionArguments>`
    '''
    from tmlib.workflow.args import SubmissionArguments
    def decorator(cls):
        if SubmissionArguments not in inspect.getmro(cls):
            raise TypeError(
                'Registered class must be derived from '
                'tmlib.workflow.args.SubmissionArguments'
            )
        _step_register[name]['submission_args'] = cls
        return cls
    return decorator


def get_step_args(name):
    '''Gets step-specific implementations of
    :class:`ArgumentCollection <tmlib.workflow.args.ArgumentCollection>`
    classes.

    Parameters
    ----------
    name: str
        name of the step

    Returns
    -------
    Tuple[Union[tmlib.workflow.args.BatchArguments, tmlib.workflow.args.SubmissionArguments]]
        class for batch and submission arguments
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
    try:
        batch_args = _step_register[name]['batch_args']
        submission_args = _step_register[name]['submission_args']
        return (batch_args, submission_args)
    except KeyError:
        raise RegistryError(
            'Arguments are not registered for step "%s".' % name
        )


def get_step_api(name):
    '''Gets the step-specific implementation of the
    :class:`WorkflowStepAPI <tmlib.workflow.api.WorkflowStepAPI>` *API* class.

    Parameters
    ----------
    name: str
        name of the step

    Returns
    -------
    classobj
        API class
    '''
    module_name = '%s.%s.api' % (__name__, name)
    try:
        module = importlib.import_module(module_name)
    except ImportError as error:
        raise ImportError(
            'Importing module "%s" failed: %s' % (module_name, error)
        )
    except:
        raise
    try:
        return _step_register[name]['api']
    except KeyError:
        raise RegistryError('No API registered for step "%s".' % name)


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

    See also
    --------
    :func:`tmlib.workflow.register_step_api`
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


from workflow import Workflow
from workflow import WorkflowStep
from workflow import ParallelWorkflowStage
from workflow import SequentialWorkflowStage
