import numpy as np
import pandas as pd
from sklearn import svm

from tmlib.models import MapobjectType, Feature, FeatureValue

from tmaps.tool.result import LabelResult
from tmaps.extensions import db


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

        kernel has to be one of:
            "rbf", "linear"

        """
        # Get mapobject
        mapobject_type_name = payload['chosen_object_type']
        mapobject_type = db.session.query(MapobjectType).\
            filter_by(name=mapobject_type_name).first()

        # Get features
        feature_names = set(payload['selected_features'])
        features = db.session.query(Feature).filter(
            (Feature.name.in_(feature_names)) &
            (Feature.mapobject_type_id == mapobject_type.id)
        ).all()

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

        # Get the optional kernel argument
        kernel = payload.get('kernel')

        clf = svm.LinearSVC()

        clf.fit(X_train, y_train)
        y_pred = clf.predict(X_pred)

        all_object_ids = training_ids + X_pred.index.tolist()
        all_object_labels = y_train.tolist() + y_pred.tolist()

        unique_labels = set(all_object_labels)
        label_number_map = dict(zip(unique_labels, range(len(unique_labels))))
        all_object_labels = [label_number_map[l] for l in all_object_labels]

        response = LabelResult(
            ids=all_object_ids, labels=all_object_labels,
            mapobject_type=mapobject_type, session=session)

        return response
        # predicted_labels = self._classify(
        #     mapobject_type, features, kernel)
        # ids = range(len(predicted_labels))

        # response = LabelResult(
        #     ids=ids, labels=predicted_labels,
        #     mapobject_type=mapobject_type, session=session)

        # return response


    # def _classify(self, mapobject_type, , feature_names, k):
    #     """Cluster map objects of a given type based on a set of selected features.
        
    #     Parameters
    #     ----------
    #     data : h5py dataset
    #         The experiments dataset.
    #     object_type : str
    #         The object type as a string. This will be used to index into the dataset.
    #     feature_names : List[str]
    #         A list of feature names on which to cluster the examples.
    #     k : int
    #         The number of clusters to find.
        
    #     Returns
    #     -------
    #     np.array
    #         An array of predicted cluster labels for all objects of the chosen type.
        
    #     """
    #     from scipy.cluster.vq import kmeans, vq

    #     ### Build training data set
    #     # Construct design matrix from features and objects that were selected.
    #     # Select the HDF5 group for the chosen object type, e.g. 'cells' or 'nuclei'.
    #     object_data = data['/objects/%s' % object_type]

    #     # Go through all features that should be used in training.
    #     # Build the matrix of all data points by stacking the feature vectors 
    #     # horizontally.
    #     feature_vectors = []
    #     for f in feature_names:
    #         feature_array_1d = object_data['features/%s' % f][()]
    #         column_vector = feature_array_1d.reshape((len(feature_array_1d), 1))
    #         feature_vectors.append(column_vector)
    #     X = np.hstack(feature_vectors)

    #     # Compute the cluster centroids
    #     # centroids is a (k, p) where each row is a centroid in the
    #     # p-dimensional feature space
    #     centroids, _ = kmeans(X, k)
    #     # Assign each example/obs to its nearest centroid
    #     # and return a vector of length N indicating the cluster to which
    #     # each observation is to be assigned (as an integer).
    #     clusterlabels, _ = vq(X, centroids)

    #     return clusterlabels.tolist()

