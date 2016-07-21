import logging
from scipy.cluster.vq import kmeans, vq

from tmserver.toolbox.classifier import UnsupervisedClassifier

logger = logging.getLogger(__name__)

class KMeans(UnsupervisedClassifier):

    def classify_sklearn(self, feature_data, k):
        # Compute the cluster centroids
        # centroids is a (k, p) where each row is a centroid in the
        # p-dimensional feature space
        centroids, _ = kmeans(feature_data, k)
        # Assign each example/obs to its nearest centroid
        # and return a vector of length N indicating the cluster to which
        # each observation is to be assigned (as an integer).
        predictions, _ = vq(feature_data, centroids)
        return zip(feature_data.index.tolist(), predictions.tolist())

    def classify_spark(self, feature_data, k):
        from pyspark.ml.clustering import KMeans as KMeansClassifier
        logger.info('perform clustering via Spark on cluster')
        kmeans = KMeansClassifier(k=k, seed=1)
        model = kmeans.fit(feature_data)
        predictions = model.transform(feature_data).\
            select('prediction', 'mapobject_id')
        logger.info('collect predicted labels')
        result = predictions.collect()
        logger.info('return predicted labels')
        return [(r.mapobject_id, r.prediction) for r in result]

