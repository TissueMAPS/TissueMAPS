# TmLibrary - TissueMAPS library for distibuted image analysis routines.
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
'''
Utility functions for dynamic import.
'''
import importlib


def load_method_args(method_name):
    '''
    Load general arguments that can be parsed to a method of
    an implemented subclass of a :class:`tmlib.cli.WorkflowStepCLI`
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
    module = importlib.import_module('tmlib.workflow.args')
    try:
        class_name = '%sArgs' % method_name.capitalize()
    except ImportError:
        raise AttributeError('Method "%s" is not available.')
    return getattr(module, class_name)


def load_var_method_args(step_name, method_name):
    '''
    Load variable step-specific arguments that can be parsed to
    a method of an implemented subclass of a
    :class:`tmlib.cli.WorkflowStepCLI` base class.

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
    package_name = 'tmlib.workflow.%s' % step_name
    module_name = 'tmlib.workflow.%s.args' % step_name
    importlib.import_module(package_name)
    module = importlib.import_module(module_name)
    class_name = '%s%sArgs' % (step_name.capitalize(),
                               method_name.capitalize())
    try:
        return getattr(module, class_name)
    except AttributeError:
        return None
