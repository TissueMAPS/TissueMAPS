import numpy as np
import pandas as pd
import logging

import tmlib.models as tm
from tmserver.tool import HeatmapLabelLayer, ToolResult
from tmserver.tool import Tool

logger = logging.getLogger(__name__)


class Heatmap(Tool):

    __icon__ = 'HMP'

    __description__ = '''
        Color codes mapobjects according to the value of a selected feature.
    '''

    def process_request(self, payload, session_id, experiment_id, use_spark=False):
        """
        {
            "chosen_object_type": str,
            "selected_feature": str
        }

        """
        mapobject_type_name = payload['chosen_object_type']
        mapobject_type = experiment.get_mapobject_type(mapobject_type_name)

        selected_feature = payload['selected_feature']

        with tm.utils.ExperimentSession(experiment_id) as session:
            feature_id = session.query(tm.Feature.id).\
                join(tm.MapobjectType).\
                filter(
                    tm.Feature.name == selected_feature,
                    tm.MapobjectType.id == mapobject_type.id,
                    tm.MapobjectType.experiment_id == experiment.id
                ).\
                one()[0]

        logger.info('calculate min/max for rescaling of intensities')
        if use_spark:
            import pyspark.sql.functions as sp
            feature_values = self.get_feature_values_spark(
                experiment_id, mapobject_type_name, selected_feature
            )
            stats = feature_values.\
                select(sp.min('value'), sp.max('value')).\
                collect()
            lower_bound = stats[0][0]
            upper_bound = stats[0][1]
        else:
            feature_values = self.get_feature_values_sklearn(
                experiment.id, mapobject_type_name, selected_feature
            )
            lower_bound = np.min(feature_values.value)
            upper_bound = np.max(feature_values.value)

        extra_attributes = {
            'feature_id': feature_id,
            'min': lower_bound,
            'max': upper_bound
        }

        logger.info('return tool result')
        return ToolResult(
            tool_session=session,
            layer=HeatmapLabelLayer(
                 mapobject_type_id=mapobject_type.id,
                 extra_attributes=extra_attributes
            )
        )
