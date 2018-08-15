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
import pandas as pd
import logging

import tmlib.models as tm
from tmlib.utils import same_docstring_as

from tmlib.tools.base import Tool, Classifier

logger = logging.getLogger(__name__)


class Clustering(Classifier):

    __icon__ = 'CLU'

    __description__ = 'Clusters mapobjects based on a set of selected features.'

    __options__ = {'method': ['kmeans'] }

    @same_docstring_as(Tool.__init__)
    def __init__(self, experiment_id):
        super(Clustering, self).__init__(experiment_id)

    def process_request(self, submission_id, payload):
        '''Processes a client tool request and inserts the generated result
        into the database. The `payload` is expected to have the following
        form::

            {
                "choosen_object_type": str,
                "selected_features": [str, ...],
                "options": {
                    "method": str,
                    "k": int
                }
            }

        Parameters
        ----------
        submission_id: int
            ID of the corresponding job submission
        payload: dict
            description of the tool job
        '''
        logger.info('perform unsupervised classification')
        mapobject_type_name = payload['chosen_object_type']
        feature_names = payload['selected_features']
        k = payload['options']['k']
        method = payload['options']['method']

        if method not in self.__options__['method']:
            raise ValueError('Unknown method "%s".' % method)

        result_id = self.register_result(
                submission_id, mapobject_type_name,
                result_type='ScalarToolResult', unique_labels=np.arange(k)
                )

        n_train = 10**5
        logger.debug('use %d objects for training', n_train)
        mapobject_ids = self.get_random_mapobject_subset(
            mapobject_type_name, n_train
        )
        logger.info('train classifier')
        training_set = self.load_feature_values(
            mapobject_type_name, feature_names, mapobject_ids
        )
        model, scaler = self.train_unsupervised(training_set, k, method)

        n_test = 10**5
        logger.debug('set batch size to %d', n_test)
        batches = self.partition_mapobjects(mapobject_type_name, n_test)
        counter = 0
        for mapobject_ids in batches:
            logger.info('predict labels for batch #%d', counter)
            counter += 1
            test_set = self.load_feature_values(
                mapobject_type_name, feature_names, mapobject_ids
            )
            predicted_labels = self.predict(test_set, model, scaler)
            self.save_result_values(
                mapobject_type_name, result_id, predicted_labels
            )
