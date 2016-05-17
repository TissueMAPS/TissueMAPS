from scipy.cluster.vq import kmeans, vq
from pyspark.ml.clustering import KMeans as KMeansClassifier

from tools.classifier import UnsupervisedClassifier


class KMeans(UnsupervisedClassifier):

    def classify_sklearn(self, feature_data, k):
        # Compute the cluster centroids
        # centroids is a (k, p) where each row is a centroid in the
        # p-dimensional feature space
        centroids, _ = kmeans(feature_data, k)
        # Assign each example/obs to its nearest centroid
        # and return a vector of length N indicating the cluster to which
        # each observation is to be assigned (as an integer).
        predictions, _ = vq(feature, centroids)
        return zip(feature_data.index.tolist(), predictions.tolist())

    def classify_spark(self, feature_data, k):
        kmeans = KMeansClassifier(k=k, seed=1)
        model = kmeans.fit(feature_data)
        predictions = model.transform(feature_data).\
            select('prediction', 'mapobject_id')
        result = predictions.collect()
        return [(r.mapobject_id, r.prediction) for r in result]

