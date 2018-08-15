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


_workflow_register = dict()


class _WorkflowDependenciesMeta(ABCMeta):

    def __init__(self, name, bases, d):
        ABCMeta.__init__(self, name, bases, d)
        required_attrs = {
            'STAGES': list,
            'STAGE_MODES': dict,
            'STEPS_PER_STAGE': dict,
            'INTER_STAGE_DEPENDENCIES': dict,
            'INTRA_STAGE_DEPENDENCIES': dict,
            '__type__': str
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
        _workflow_register[getattr(self, '__type__')] = self


class WorkflowDependencies(object):

    '''Abstract base class for declartion of workflow dependencies.

    Derived classes will be used by descriptor classes in
    :mod:`tmlib.worklow.description` to declare a workflow `type`.

    In addtion, derived classes must implement the following attributes:

        * ``__type__``: name of the workflow type
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

    __metaclass__ = _WorkflowDependenciesMeta

    __abstract__ = True


class CanonicalWorkflowDependencies(WorkflowDependencies):

    '''Declaration of dependencies for the canonical workflow.'''

    __type__ = 'canonical'

    #: List[str]: names of workflow stages
    STAGES = [
        'image_conversion', 'image_preprocessing',
        'pyramid_creation', 'image_analysis'
    ]

    #: Dict[str, str]: mode for each workflow stage, i.e. whether setps of a stage
    #: should be submitted in parallel or sequentially
    STAGE_MODES = {
        'image_conversion': 'sequential',
        'image_preprocessing': 'parallel',
        'pyramid_creation': 'sequential',
        'image_analysis': 'sequential'
    }

    #: collections.OrderedDict[str, List[str]]: names of steps within each stage
    STEPS_PER_STAGE = {
        'image_conversion':
            ['metaextract', 'metaconfig', 'imextract'],
        'image_preprocessing':
            ['corilla'],
        'pyramid_creation':
            ['illuminati'],
        'image_analysis':
            ['jterator']
    }

    #: collections.OrderedDict[str, Set[str]]: dependencies between workflow stages
    INTER_STAGE_DEPENDENCIES = {
        'image_conversion': {

        },
        'image_preprocessing': {
            'image_conversion'
        },
        'pyramid_creation': {
            'image_conversion', 'image_preprocessing'
        },
        'image_analysis': {
            'image_conversion', 'image_preprocessing'
        }
    }

    #: Dict[str, Set[str]: dependencies between workflow steps within one stage
    INTRA_STAGE_DEPENDENCIES = {
        'metaextract': {

        },
        'metaconfig': {
            'metaextract'
        },
        'imextract': {
            'metaconfig'
        }
    }


class MultiplexingWorkflowDependencies(CanonicalWorkflowDependencies):

    '''Declaration of dependencies for a multiplexing workflow, which includes
    the :mod:`algin <tmlib.workflow.align>` step.
    '''

    __type__ = 'multiplexing'

    #: Dict[str, str]: mode for each workflow stage, i.e. whether setps of a stage
    #: should be submitted in parallel or sequentially
    STAGE_MODES = {
        'image_conversion': 'sequential',
        'image_preprocessing': 'sequential',
        'pyramid_creation': 'sequential',
        'image_analysis': 'sequential'
    }

    #: Dict[str, List[str]]: names of steps within each stage
    STEPS_PER_STAGE = {
        'image_conversion':
            ['metaextract', 'metaconfig', 'imextract'],
        'image_preprocessing':
            ['corilla', 'align'],
        'pyramid_creation':
            ['illuminati'],
        'image_analysis':
            ['jterator']
    }



def get_workflow_type_information():
    '''Gets the names of each implemented workflow type.

    Returns
    -------
    Set[str]
        names of workflow types

    See also
    --------
    :func:`tmlib.workflow.register_workflow_type`
    '''
    return set(_workflow_register.keys())


def get_workflow_dependencies(name):
    '''Gets a workflow type specific implementation of
    :class:`WorkflowDependencies <tmlib.workflow.dependencies.WorkflowDependencies>`.

    Parameters
    ----------
    name: str
        name of the workflow type

    Returns
    -------
    classobj
    '''
    return _workflow_register[name]


