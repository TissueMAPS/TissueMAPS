# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016-2018 University of Zurich.
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
import re
import numpy as np
import pandas as pd
import logging

import tmlib.models as tm
from tmlib.utils import same_docstring_as

from tmlib.tools.base import Tool

logger = logging.getLogger(__name__)


class Heatmap(Tool):

    __icon__ = 'HMP'

    __description__ = '''
        Color codes mapobjects according to the value of a selected feature.
    '''

    @same_docstring_as(Tool.__init__)
    def __init__(self, experiment_id):
        super(Heatmap, self).__init__(experiment_id)

    def _get_feature_id(self, mapobject_type_name, feature_name):
        '''Gets the ID of a feature.

        Parameters
        ----------
        mapobject_type_name: str
            name of the corresponding
            :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`
        feature_name: str
            name of the :class:`Feature <tmlib.models.feature.Feature>`

        Returns
        -------
        int
            feature ID
        '''
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            feature = session.query(tm.Feature.id).\
                join(tm.MapobjectType).\
                filter(
                    tm.Feature.name == feature_name,
                    tm.MapobjectType.name == mapobject_type_name
                ).\
                one()
            return feature.id

    def process_request(self, submission_id, payload):
        '''Processes a client tool request, where the `payload` is expected to
        have the following form::

            {
                "choosen_object_type": str,
                "selected_feature": str
            }


        Parameters
        ----------
        submission_id: int
            ID of the corresponding job submission
        payload: dict
            description of the tool job
        '''
        mapobject_type_name = payload['chosen_object_type']
        selected_feature = payload['selected_feature']

        logger.info('calculate min/max for rescaling of intensities')
        lower, upper = self.calculate_extrema(
            mapobject_type_name, selected_feature
        )

        if np.isnan(lower):
            raise ValueError('Minimum feature value is NaN.')
        if np.isnan(upper):
            raise ValueError('Maximum feature value is NaN.')

        feature_id = self._get_feature_id(mapobject_type_name, selected_feature)
        result_id = self.register_result(
            submission_id, mapobject_type_name,
            result_type='HeatmapToolResult',
            feature_id=feature_id, min=lower, max=upper
        )

        # NOTE: This tool doesn't generate any new labels, but uses already
        # existing feature values.
