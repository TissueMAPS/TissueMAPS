from scipy.cluster.vq import kmeans, vq
from tmaps.tool import ScalarLabelLayer, Result
from tmaps.extensions import db
from tmlib.models import MapobjectType


class ClusterTool():
    def process_request(self, payload, session, experiment):
        """
        {
            "chosen_object_type": str,
            "selected_features": List[str],
            "k": int
        }

        """
        # Get mapobject
        mapobject_type_name = payload['chosen_object_type']
        mapobject_type = db.session.query(MapobjectType).\
            filter_by(
                name=mapobject_type_name, experiment_id=experiment.id
            ).\
            one()

        # Get features
        feature_names = set(payload['selected_features'])
        X = mapobject_type.get_feature_value_matrix(feature_names)

        # Get model parameters
        k = payload['k']

        predicted_labels = self._perform_clustering(X, k)
        ids = X.index.tolist()

        labels = dict(zip(ids, predicted_labels))

        result = Result(
            tool_session=session,
            layer=ScalarLabelLayer(labels=labels)
        )

        return result

    def _perform_clustering(self, X, k):
        """Cluster map objects of a given type based on a set of selected features.

        Parameters
        ----------
        X : pandas.DataFrame
            A matrix-style data frame with columns as feature vectors and
            rows as mapobjects.
        k : int
            The number of clusters to find.

        Returns
        -------
        np.array
            An array of predicted cluster labels for all objects of
            the chosen type.

        """
        # Compute the cluster centroids
        # centroids is a (k, p) where each row is a centroid in the
        # p-dimensional feature space
        centroids, _ = kmeans(X, k)
        # Assign each example/obs to its nearest centroid
        # and return a vector of length N indicating the cluster to which
        # each observation is to be assigned (as an integer).
        clusterlabels, _ = vq(X, centroids)

        return clusterlabels.tolist()
