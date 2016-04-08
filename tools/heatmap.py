import numpy as np
import matplotlib
from matplotlib import cm

from tmlib.models import Feature, FeatureValue, MapobjectType
from tmaps.extensions import db
from tmaps.tool.result import LabelResult

class HeatmapResult(LabelResult):
    def __init__(self, *args, **kwargs):
        super(HeatmapResult, self).__init__(*args, result_type='HeatmapResult', **kwargs)

class HeatmapTool():
    def process_request(self, payload, session, experiment):
        """
        {
            "chosen_object_type": str,
            "selected_feature": str
        }

        """
        # Get mapobject
        mapobject_type_name = payload['chosen_object_type']
        mapobject_type = db.session.query(MapobjectType).\
            filter_by(name=mapobject_type_name).first()

        selected_feature = payload['selected_feature']

        # Get features
        query_result = db.session.query(
            FeatureValue.mapobject_id, FeatureValue.value).\
            join(Feature).\
            join(MapobjectType).\
            filter(Feature.name == selected_feature).all()

        mapobject_ids = [q.mapobject_id for q in query_result]
        values = [q.value for q in query_result]

        minval = np.min(values)
        maxval = np.max(values)

        response = HeatmapResult(
            ids=mapobject_ids, labels=values, mapobject_type=mapobject_type,
            session=session, attributes={
                'min': minval,
                'max': maxval
            }
        )

        return response
