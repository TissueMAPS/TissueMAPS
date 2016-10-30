# TmLibrary - TissueMAPS library for distibuted image processing routines.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
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

A `workflow` is a sequence of distributed computational tasks
(`steps`). Each `step` represents a collection of batch jobs that can be
processed in parallel. It is comprised of the following phases:

    * **init**: Paritioning of the computational task into smaller batches
      based on user provided arguments.
    * **run**: Scheduled parallel processing of individual batches according to
      user defined resource allocation.
    * **collect** (optional): Postprocessing of results obtained by individual
      batch jobs.

A `step` is implemented as a subpackage of `tmlib.workflow` containing
three modules:

    * **args**: Must implemement :class:`tmlib.workflow.args.BatchArguments` and
      :class:`tmlib.workflow.args.SubmissionArguments` and decorate them with
      :func:`tmlib.workflow.register_batch_args` and
      :func:`tmlib.workflow.register_submission_args`, respectively. These
      classes provide `step`-specific arguments that control the
      partitioning of the given computational task into separate batch jobs
      and the amount of computational resources, which should get allocated
      to each batch job.
    * **api**: Must implement :class:`tmlib.workflow.api.ClusterRoutines` and
      decorate it with :func:`tmlib.workflow.register_api`. This class
      provides the active programming interface (API) with methods for
      creation and management of batch jobs. The methods
      :meth:`tmlib.workflow.api.ClusterRoutines.create_batches`,
      :meth:`tmlib.workflow.api.ClusterRoutines.run_job` and
      :meth:`tmlib.workflow.api.ClusterRoutines.collect_job_output` implemented
      by derived classes are responsible for the `step`-specific processing
      behaviour and controlled via the `batch` and `submission` arguments
      described above.
    * **cli**: Must implement :class:`tmlib.workflow.cli.CommandLineInterface`.
      This class provides the command line interface (CLI) and main entry points
      for the program. It supplies high-level methods for the different
      `phases`, which delegate processing to the respective API methods.

This implementation automatically registers a `step` and makes it available
for integration into larger workflows.
To this end, `steps` are further combined into abstract task collections
referred to as `stages`. A `stage` bundles one ore more `steps`
into a logical processing unit taking potential dependencies between them
into account.

A :class:`tmlib.workflow.workflow.Workflow` is dynamically build from `steps`
based on :class:`tmlib.workflow.description.WorkflowDescription` - a description
provided by users as a mapping in `YAML` format.
The `workflow` structure, i.e. the sequence of `stages` and `steps` and their
interdependencies, is defined by its `type`, which is determined based on an
implementation of :class:`tmlib.workflow.dependencies.WorkflowDependencies`.
To make a `type` available for use, the derived class must be
registered via :func:`register_workflow_type`. An example is the "canonical"
`type` declared by
:class:`tmlib.workflow.canonical.CanonicalWorkflowDependencies`.

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
    '''Gets a specific implementation of
    :class:`tmlib.workflow.dependencies.WorkflowDependencies`.

    Parameters
    ----------
    name: str
        name of the workflow type

    Returns
    -------
    classobj
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


