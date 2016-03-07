from collections import defaultdict

from scipy.cluster.vq import kmeans, vq
import numpy as np
from matplotlib import cm
import numpy as np
from tmaps.tool.result import LabelResult


class ClusterTool():
    def process_request(self, payload, session, experiment):
        """
        {
            "chosen_object_type": str,
            "selected_features": List[str],
            "k": int
        }

        """

        feature_names = payload['selected_features']
        mapobject_name = payload['chosen_object_type']
        k = payload['k']

        with experiment.dataset as dataset:
            predicted_labels = self._perform_clustering(
                dataset, mapobject_name, feature_names, k)
            ids = range(len(predicted_labels))
        response = LabelResult(
            ids=ids, labels=predicted_labels, mapobject_name=mapobject_name,
            session=session)

        return response


    def _perform_clustering(self, data, object_type, feature_names, k):
        """Cluster map objects of a given type based on a set of selected features.
        
        Parameters
        ----------
        data : h5py dataset
            The experiments dataset.
        object_type : str
            The object type as a string. This will be used to index into the dataset.
        feature_names : List[str]
            A list of feature names on which to cluster the examples.
        k : int
            The number of clusters to find.
        
        Returns
        -------
        np.array
            An array of predicted cluster labels for all objects of the chosen type.
        
        """
        from scipy.cluster.vq import kmeans, vq

        ### Build training data set
        # Construct design matrix from features and objects that were selected.
        # Select the HDF5 group for the chosen object type, e.g. 'cells' or 'nuclei'.
        object_data = data['/objects/%s' % object_type]

        # Go through all features that should be used in training.
        # Build the matrix of all data points by stacking the feature vectors 
        # horizontally.
        feature_vectors = []
        for f in feature_names:
            feature_array_1d = object_data['features/%s' % f][()]
            column_vector = feature_array_1d.reshape((len(feature_array_1d), 1))
            feature_vectors.append(column_vector)
        X = np.hstack(feature_vectors)

        # Compute the cluster centroids
        # centroids is a (k, p) where each row is a centroid in the
        # p-dimensional feature space
        centroids, _ = kmeans(X, k)
        # Assign each example/obs to its nearest centroid
        # and return a vector of length N indicating the cluster to which
        # each observation is to be assigned (as an integer).
        clusterlabels, _ = vq(X, centroids)

        return clusterlabels.tolist()

