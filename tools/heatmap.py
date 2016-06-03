import numpy as np
import pandas as pd
import logging

from tmlib.models import Feature, FeatureValue, MapobjectType
from tmaps.extensions import db
from tmaps.tool import HeatmapLabelLayer, Result
from tmaps.tool import ToolRequestHandler

logger = logging.getLogger(__name__)


class Heatmap(ToolRequestHandler):
    def process_request(self, payload, session, experiment, use_spark=False):
        """
        {
            "chosen_object_type": str,
            "selected_feature": str
        }

        """
        mapobject_type_name = payload['chosen_object_type']
        mapobject_type = experiment.get_mapobject_type(mapobject_type_name)

        selected_feature = payload['selected_feature']

        feature_id = db.session.query(Feature.id).\
            join(MapobjectType).\
            filter(
                Feature.name == selected_feature,
                MapobjectType.id == mapobject_type.id,
                MapobjectType.experiment_id == experiment.id
            ).\
            one()[0]

        logger.info('calculate min/max for rescaling of intensities')
        if use_spark:
            import pyspark.sql.functions as sp
            feature_values = self.get_feature_values_spark(
                experiment.id, mapobject_type_name, selected_feature
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
            upper_bound = np.max(feature_value.value)

        extra_attributes = {
            'feature_id': feature_id,
            'min': lower_bound,
            'max': upper_bound
        }

        logger.info('return tool result')
        return Result(
            tool_session=session,
            layer=HeatmapLabelLayer(
                 mapobject_type_id=mapobject_type.id,
                 extra_attributes=extra_attributes
            )
        )
