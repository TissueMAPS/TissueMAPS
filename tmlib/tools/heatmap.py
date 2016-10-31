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
import numpy as np
import pandas as pd
import logging

import tmlib.models as tm
from tmlib.utils import same_docstring_as

from tmlib.tools.base import Tool
from tmlib.tools.result import ToolResult, HeatmapLabelLayer

logger = logging.getLogger(__name__)


class Heatmap(Tool):

    __icon__ = 'HMP'

    __description__ = '''
        Color codes mapobjects according to the value of a selected feature.
    '''

    @same_docstring_as(Tool.__init__)
    def __init__(self, experiment_id):
        super(Heatmap, self).__init__(experiment_id)

    def process_request(self, payload):
        '''Processes a client tool request.
        The `payload` is expected to have the following form::

            {
                "choosen_object_type": str,
                "selected_feature": str
            }


        Parameters
        ----------
        payload: dict
            description of the tool job
        '''
        mapobject_type_name = payload['chosen_object_type']
        selected_feature = payload['selected_feature']

        logger.info('calculate min/max for rescaling of intensities')
        if self.use_spark:
            import pyspark.sql.functions as sp
            feature_values = self.get_feature_values_spark(
                mapobject_type_name, selected_feature
            )
            stats = feature_values.\
                select(sp.min('value'), sp.max('value')).\
                collect()
            lower_bound = stats[0][0]
            upper_bound = stats[0][1]
        else:
            feature_values = self.get_feature_values_sklearn(
                mapobject_type_name, selected_feature
            )
            lower_bound = np.min(feature_values.value)
            upper_bound = np.max(feature_values.value)


        # This tool doesn't generate any new labels, but uses already
        # existing feature values.
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            mapobject_type = session.query(tm.MapobjectType).\
                filter_by(name=mapobject_type_name).\
                one()
            feature = session.query(tm.Feature).\
                join(tm.MapobjectType).\
                filter(
                    tm.Feature.name == selected_feature,
                    tm.MapobjectType.name == mapobject_type_name
                ).\
                one()

            result = ToolResult(self.submission_id, self.__class__.__name__)
            session.add(result)
            session.flush()

            layer = HeatmapLabelLayer(
                result.id, mapobject_type.id,
                feature_id=feature.id, min=lower_bound, max=upper_bound
            )
            session.add(layer)
