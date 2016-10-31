# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import numpy as np
import logging

import tmlib.models as tm
from tmlib.utils import same_docstring_as
from tmlib.tools import register_tool

from tmlib.tools.base import Tool, Classifier

logger = logging.getLogger(__name__)


@register_tool('Clustering')
class Clustering(Classifier):

    __icon__ = 'CLU'

    __description__ = '''
        Clusters mapobjects based on a set of selected features.
    '''

    __methods__ = ['kmeans']

    @same_docstring_as(Tool.__init__)
    def __init__(self, experiment_id):
        super(Clustering, self).__init__(experiment_id)

    def classify(self, feature_data, k, method):
        '''Clusters mapobjects based on `feature_data` using the
        machine learning library.

        Parameters
        ----------
        feature_data: pyspark.sql.DataFrame or pandas.DataFrame
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
        if self.use_spark:
            return self._classify_spark(feature_data, k, method)
        else:
            return self._classify_sklearn(feature_data, k, method)

    def _classify_sklearn(self, feature_data, k, method):
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
        # Ensure that values are JSON serializable
        predictions = clf.labels_.astype(int).tolist()
        mapobject_ids = feature_data.index.astype(int).tolist()
        return zip(mapobject_ids, predictions)

    def _classify_spark(self, feature_data, k, method):
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

    def process_request(self, submission_id, payload):
        '''Processes a client tool request and inserts the generated result
        into the database. The `payload` is expected to have the following
        form::

            {
                "choosen_object_type": str,
                "selected_features": [str, ...],
                "method": str,
                "k": int
            }


        Parameters
        ----------
        submission_id: int
            ID of the corresponding job submission
        payload: dict
            description of the tool job
        '''
        mapobject_type_name = payload['chosen_object_type']
        feature_names = payload['selected_features']
        k = payload['k']
        method = payload['method']

        if method not in self.__methods__:
            raise ValueError('Unknown method "%s".' % method)

        feature_data = self.format_feature_data(
            mapobject_type_name, feature_names
        )
        predicted_labels = self.classify(feature_data, k, method)

        with tm.utils.ExperimentSession(self.experiment_id) as session:
            mapobject_type = session.query(tm.MapobjectType).\
                filter_by(name=mapobject_type_name).\
                one()

            result = tm.ToolResult(submission_id, self.__class__.__name__)
            session.add(result)
            session.flush()

            unique_labels = np.unique(np.array(predicted_labels)[:, 1]).tolist()
            layer = tm.ScalarLabelLayer(
                result.id, mapobject_type.id, unique_labels
            )
            session.add(layer)
            session.flush()

            label_objs = [
                {
                    'label': value,
                    'mapobject_id': mapobject_id,
                    'label_layer_id': layer.id
                }
                for mapobject_id, value in predicted_labels
            ]
            session.bulk_insert_mappings(tm.LabelLayerValue, label_objs) 

