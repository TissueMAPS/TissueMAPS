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
import logging

from tmlib.workflow.dependencies import WorkflowDependencies
from tmlib.workflow import register_workflow_type

logger = logging.getLogger(__name__)


@register_workflow_type('canonical')
class CanonicalWorkflowDependencies(WorkflowDependencies):

    '''Declaration of dependencies for the canonical workflow.'''

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
