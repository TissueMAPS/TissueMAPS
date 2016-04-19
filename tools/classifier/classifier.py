import numpy as np
import pandas as pd

from tmlib.models import FeatureValue, Feature, MapobjectType
from tmaps.extensions import db
from tmaps.tool.result import LabelResult


class ClassifierTool(object):
    def process_request(self, payload, session, experiment):
        # Get mapobject
        mapobject_type_name = payload['chosen_object_type']
        mapobject_type = db.session.query(MapobjectType).\
            filter_by(name=mapobject_type_name).first()

        # Get features
        feature_names = set(payload['selected_features'])
        feature_values = db.session.query(
            Feature.name, FeatureValue.mapobject_id, FeatureValue.value).\
            join(FeatureValue).\
            filter(
                (Feature.name.in_(feature_names)) &
                (Feature.mapobject_type_id == mapobject_type.id)).all()
        feature_df_long = pd.DataFrame(feature_values)
        feature_df_long.columns = ['feature', 'mapobject', 'value']
        feature_df = pd.pivot_table(
            feature_df_long, values='value', index='mapobject', columns='feature')

        # Get classes:
        Xs = []
        ys = []
        training_ids = []
        for cls in payload['training_classes']:
            ids = cls['object_ids']
            training_ids += ids
            X = feature_df.loc[ids]
            Xs.append(X)
            y = np.repeat(cls['name'], len(ids))
            ys.append(y)

        y_train = np.concatenate(ys)
        X_train = np.vstack(Xs)

        X_pred = feature_df[~feature_df.index.isin(training_ids)]

        y_pred = self.classify(X_train, y_train, X_pred)

        all_object_ids = training_ids + X_pred.index.tolist()
        all_object_labels = y_train.tolist() + y_pred.tolist()

        unique_labels = set(all_object_labels)
        label_number_map = dict(zip(unique_labels, range(len(unique_labels))))
        all_object_labels = [label_number_map[l] for l in all_object_labels]

        response = LabelResult(
            ids=all_object_ids, labels=all_object_labels,
            mapobject_type_id=mapobject_type.id, session_id=session_id)

        return response

    def classify(X_train, y_train, X_pred):
        raise Exception('Abstract function')
