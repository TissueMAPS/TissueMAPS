import logging

from tmlib.workflow.canonical import CanonicalWorkflowDependencies
from tmlib.workflow import register_workflow_type

logger = logging.getLogger(__name__)


@register_workflow_type('multiplexing')
class MultiplexingWorkflowDependencies(CanonicalWorkflowDependencies):

    '''Declaration of dependencies for a multiplexing workflow, which includes
    the :module:`tmlib.workflow.align` step.
    '''

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
