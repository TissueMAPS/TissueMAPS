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
import numpy as np
import pandas as pd
import logging

import tmlib.models as tm
from tmlib.utils import same_docstring_as

from tmlib.tools.base import Tool

logger = logging.getLogger(__name__)


class Aggregation(Tool):

    __icon__ = 'AGG'

    __description__ = '''
        Aggregates feature values of all mapobjects of a given type that
        fall within larger mapobjects of a different type.
    '''

    @same_docstring_as(Tool.__init__)
    def __init__(self, experiment_id):
        super(Aggregation, self).__init__(experiment_id)

    @same_docstring_as(Tool.process_request)
    def process_request(self, submission_id, payload):
        pass
