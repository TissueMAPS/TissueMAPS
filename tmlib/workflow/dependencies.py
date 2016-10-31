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
import collections
from abc import ABCMeta


class WorkflowDependenciesMeta(ABCMeta):

    '''Metaclass for :class:`tmlib.workflow.dependencies.WorkflowDependencies`.

    Raises
    ------
    AttributeError:
        when classes derived from
        :class:`tmlib.workflow.dependencies.WorkflowDependencies` don't
        implement any of the required class attributes
    TypeError:
        when the implemented class attributes don't have the correct type
    '''

    def __init__(self, name, bases, d):
        ABCMeta.__init__(self, name, bases, d)
        required_attrs = {
            'STAGES': list,
            'STAGE_MODES': dict,
            'STEPS_PER_STAGE': dict,
            'INTER_STAGE_DEPENDENCIES': dict,
            'INTRA_STAGE_DEPENDENCIES': dict
        }
        if '__abstract__' in vars(self):
            if getattr(self, '__abstract__'):
                return
        for attr_name, attr_type in required_attrs.iteritems():
            if not hasattr(self, attr_name):
                raise AttributeError(
                    'Class "%s" must implement attribute "%s".' % (
                        self.__name__, attr_name
                    )
                )
            attr_val = getattr(self, attr_name)
            if not isinstance(attr_val, attr_type):
                raise TypeError(
                    'Attribute "%s" of class "%s" must have type %s.' % (
                        attr_name, self.__name__, attr_type.__name__
                    )
                )
            # TODO: check intra_stage_dependencies inter_stage_dependencies
            # based on __dependencies__

class WorkflowDependencies(object):

    '''Abstract base class for declartion of workflow dependencies.

    Derived classes will be used by descriptor classes in
    :mod:`tmlib.worklow.description` to declare a workflow `type`.
    To this end, derived classes need to be registered using the class
    decorator :func:`tmlib.workflow.register_workflow_type`.

    In addtion, derived classes must implement the following attributes:

        * ``STAGES`` (list): names of stages that the workflow should have
        * ``STAGE_MODES`` (dict): mapping of stage name to processing mode
          (either ``"parallel"`` or ``"sequential"``)
        * ``STEPS_PER_STAGE`` (dict): ordered mapping of
          stage name to corresponding step names
        * ``INTER_STAGE_DEPENDENCIES`` (dict): mapping of stage name to names
          of other stages the referenced stage depends on
        * ``INTRA_STAGE_DEPENDENCIES`` (dict): mapping of step name to names
          of other steps the referenced step depends on

    '''

    __metaclass__ = WorkflowDependenciesMeta

    __abstract__ = True
