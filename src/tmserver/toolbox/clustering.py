import logging

from tmserver.toolbox.base import Classifier

logger = logging.getLogger(__name__)


class Clustering(Classifier):

    __icon__ = 'CLU'

    __description__ = '''
        Clusters mapobjects based on a set of selected features.
    '''

    __methods__ = ['kmeans']

    def classify_sklearn(self, feature_data, k, method):
        '''Clusters mapobjects based on `feature_data` using the
        machine learning library.

        Parameters
        ----------
        feature_data: pandas.DataFrame
            feature values
        k: int
            number of classes
        method: str
            model to use for clustering

        Returns
        -------
        List[Tuple[int, str]]
            ID and predicted label for each mapobject
        '''
        from sklearn.cluster import KMeans

        models = {
            'kmeans': KMeans
        }
        logger.info(
            'perform clustering via Scikit-Learn with "%s" method', method
        )
        clf = models[method](n_clusters=k)
        logger.info('fit model')
        clf.fit(feature_data)
        logger.info('collect predicted labels')
        predictions = clf.labels_

        # from scipy.cluster.vq import kmeans, vq
        # # Compute the cluster centroids
        # # centroids is a (k, p) where each row is a centroid in the
        # # p-dimensional feature space
        # centroids, _ = kmeans(feature_data, k)
        # # Assign each example/obs to its nearest centroid
        # # and return a vector of length N indicating the cluster to which
        # # each observation is to be assigned (as an integer).
        # predictions, _ = vq(feature_data, centroids)
        return zip(feature_data.index.tolist(), predictions)

    def classify_spark(self, feature_data, k, method):
        '''Clusters mapobjects based on `feature_data` using the
        machine learning library.

        Parameters
        ----------
        feature_data: pyspark.sql.DataFrame
            feature values
        k: int
            number of classes
        method: str
            model to use for clustering

        Returns
        -------
        List[Tuple[int, str]]
            ID and predicted label for each mapobject
        '''
        from pyspark.ml.clustering import KMeans
        models = {
            'kmeans': KMeans
        }
        logger.info('perform clustering via Spark with "%s" method', method)
        clf = models[method](k=k, seed=1)
        logger.info('fit model')
        model = clf.fit(feature_data)
        predictions = model.transform(feature_data).\
            select('prediction', 'mapobject_id')
        logger.info('collect predicted labels')
        result = predictions.collect()
        return [(r.mapobject_id, r.prediction) for r in result]

    def process_request(self, payload, session_id, experiment_id, use_spark=False):
        mapobject_type_name = payload['chosen_object_type']
        feature_names = payload['selected_features']
        k = payload['k']
        method = payload['method']

        if method not in self.__methods__:
            raise ValueError('Unknown method "%s".' % method)

        with tm.utils.ExperimentSession(experiment_id) as session:
            mapobject_type_id = session.query(tm.MapobjectType.id).\
                filter_by(name=mapobject_type_name).\
                one()

        if use_spark:
            feature_data = self.format_feature_data_spark(
                experiment.id, mapobject_type_name, feature_names
            )
            predicted_labels = self.classify_spark(feature_data, k)
        else:
            feature_data = self.format_feature_data_sklearn(
                experiment.id, mapobject_type_name, feature_names
            )
            predicted_labels = self.classify_sklearn(feature_data, k)

        return ToolResult(
            tool_session_id=session_id,
            layer=ScalarLabelLayer(
                mapobject_type_id=mapobject_type_id,
                labels=dict(predicted_labels)
            )
        )

