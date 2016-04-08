import numpy as np
import pandas as pd

from sklearn.grid_search import GridSearchCV
from sklearn import svm, cross_validation

from tmlib.models import MapobjectType, Feature, FeatureValue
from tmaps.tool.result import LabelResult
from tmaps.extensions import db
from tools.classifier import ClassifierResult


class SVMTool():
    def process_request(self, payload, session, experiment):
        """
        {
            "chosen_object_type": str,
            "selected_features": List[str],
            "kernel": str,
            "training_classes": List[
                {
                    "name": str,
                    "object_ids": List[int],
                    "color": {r: int, g: int, b: int, a: float}
                }
            ]
        }

        """
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

        n_examples = len(y_train)
        n_folds = min(n_examples / 2, 10)

        folds = cross_validation.StratifiedKFold(y_train, n_folds=n_folds)
        searchspace = [
            {'kernel': ['rbf'], 'C': np.linspace(0.1, 1, 10), 'gamma': [0.001, 0, 1]},
            {'kernel': ['linear'], 'C': np.linspace(0.1, 1, 10)}
        ]
        clf = svm.SVC()
        gs = GridSearchCV(clf, searchspace, cv=folds)
        gs.fit(X_train, y_train)

        best_params = gs.best_params_
        best_score = gs.best_score_

        y_pred = gs.predict(X_pred)

        all_object_ids = training_ids + X_pred.index.tolist()
        all_object_labels = y_train.tolist() + y_pred.tolist()

        unique_labels = list(set(all_object_labels))

        response = ClassifierResult(
            ids=all_object_ids, labels=all_object_labels,
            mapobject_type=mapobject_type, session=session, attributes={
                'labels': unique_labels
            })

        return response
