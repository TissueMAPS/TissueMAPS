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

from tmlib.workflow.canonical import CanonicalWorkflowDependencies
from tmlib.workflow import register_workflow_type

logger = logging.getLogger(__name__)


@register_workflow_type('multiplexing')
class MultiplexingWorkflowDependencies(CanonicalWorkflowDependencies):

    '''Declaration of dependencies for a multiplexing workflow, which includes
    the :mod:`algin <tmlib.workflow.align>` step.
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
