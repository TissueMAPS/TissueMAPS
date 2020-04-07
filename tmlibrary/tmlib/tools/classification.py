# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016-2018 University of Zurich.
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
import pandas as pd

import tmlib.models as tm
from tmlib.utils import same_docstring_as

from tmlib.tools.base import Tool, Classifier

logger = logging.getLogger(__name__)


class Classification(Classifier):

    '''Tool for supervised classification.'''

    __icon__ = 'SVC'

    __description__ = (
        'Classifies mapobjects based on the values of selected features and '
        'labels provided by the user.'
    )

    # TODO: Ensure that all options are available for all libraries.
    __options__ = {'method': ['randomforest', 'svm'], 'n_fold_cv': 10}

    @same_docstring_as(Tool.__init__)
    def __init__(self, experiment_id):
        super(Classification, self).__init__(experiment_id)

    def process_request(self, submission_id, payload):
        '''Processes a client tool request and inserts the generated result
        into the database.
        The `payload` is expected to have the following form::

            {
                "choosen_object_type": str,
                "selected_features": [str, ...],
                "training_classes": [
                    {
                        "name": str,
                        "object_ids": [int, ...],
                        "color": str
                    },
                    ...
                ],
                "options": {
                    "method": str,
                    "n_fold_cv": int
                }

            }

        Parameters
        ----------
        submission_id: int
            ID of the corresponding job submission
        payload: dict
            description of the tool job
        '''
        logger.info('perform supervised classification')
        mapobject_type_name = payload['chosen_object_type']
        feature_names = payload['selected_features']
        method = payload['options']['method']
        n_fold_cv = payload['options']['n_fold_cv']

        if method not in self.__options__['method']:
            raise ValueError('Unknown method "%s".' % method)

        labels = dict()
        label_map = dict()
        for i, cls in enumerate(payload['training_classes']):
            labels.update({j: float(i) for j in cls['object_ids']})
            label_map[float(i)] = {'name': cls['name'], 'color': cls['color']}

        unique_labels = np.unique(labels.values())
        #result_id = self.register_result(
        #    submission_id, mapobject_type_name,
        #    result_type='SupervisedClassifierToolResult',
        #    unique_labels=unique_labels, label_map=label_map
        #)

        # Save the labels used for this classification
        logger.info('Save current selections')
        # TODO: Make the name entered in the interface appear as the name of the saved selection
        # Also deal with potential name duplications here
        # name = payload['name']

        # Create a MultiIndex pandas.Series for the input labels, because
        # the save_results_values expects such a pandas Series.
        # Keys are mapobject ids, values are the actual labels
        # TODO: Don't hard-code tpoint 0. Check how it's done in
        # load_feature_values

        indices = []
        tpoint = 0
        for label in labels.keys():
            indices.append((label, tpoint))

        index = pd.MultiIndex.from_tuples(
            indices, names=['mapobject_id', 'tpoint']
        )

        label_array = np.array(labels.values())
        label_series = pd.Series(label_array, index=index)

        # TODO: Handle name inputs & parsing
        name = 'SavedSelection'

        label_result_id = self.register_result(
             submission_id, mapobject_type_name,
             result_type='SavedSelectionsToolResult', name=name,
             unique_labels=unique_labels, label_map=label_map
        )

        self.save_result_values(
            mapobject_type_name, label_result_id, label_series
        )

        # # Train the classifier
        # training_set = self.load_feature_values(
        #     mapobject_type_name, feature_names, labels.keys()
        # )
        # logger.info('train classifier')
        # model, scaler = self.train_supervised(
        #     training_set, labels, method, n_fold_cv
        # )
        #
        # n_test = 10**5
        # logger.debug('set batch size to %d', n_test)
        # batches = self.partition_mapobjects(mapobject_type_name, n_test)
        # for i, mapobject_ids in enumerate(batches):
        #     logger.info('predict labels for batch #%d', i)
        #     test_set = self.load_feature_values(
        #         mapobject_type_name, feature_names, mapobject_ids
        #     )
        #     predicted_labels = self.predict(test_set, model, scaler)
        #     self.save_result_values(
        #         mapobject_type_name, result_id, predicted_labels
        #     )
