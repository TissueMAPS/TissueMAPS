import collections
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
    STEPS_PER_STAGE = collections.OrderedDict({
        'image_conversion':
            ['metaextract', 'metaconfig', 'imextract'],
        'image_preprocessing':
            ['corilla'],
        'pyramid_creation':
            ['illuminati'],
        'image_analysis':
            ['jterator']
    })

    #: collections.OrderedDict[str, Set[str]]: dependencies between workflow stages
    INTER_STAGE_DEPENDENCIES = collections.OrderedDict({
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
    })

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
