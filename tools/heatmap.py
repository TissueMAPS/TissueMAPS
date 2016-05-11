from tmlib.models import Feature, FeatureValue, MapobjectType
from tmaps.extensions import db
from tmaps.tool import ContinuousLabelLayer, Result


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
        mapobject_type = experiment.get_mapobject_type(mapobject_type_name)

        selected_feature = payload['selected_feature']

        # Get feature
        query_result = db.session.query(
            FeatureValue.mapobject_id, FeatureValue.value).\
            join(Feature, MapobjectType).\
            filter(
                Feature.name == selected_feature,
                MapobjectType.id == mapobject_type.id,
                MapobjectType.experiment_id == experiment.id
            ).all()

        mapobject_ids = [q.mapobject_id for q in query_result]
        values = [q.value for q in query_result]

        labels = dict(zip(mapobject_ids, values))

        result = Result(
            tool_session=session,
            layer=ContinuousLabelLayer(labels=labels)
        )

        return result
