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
        into the database. This function delegates to one of two helper
        functions depending on the input. Because TissueMaps generates a single
        submission_id per request and the submission id is required to save
        results to the database, doing everything within the same submission
        does not work and this more complicated way was necessary.

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
                },
                "task": str (either 'classification' or 'save_labels'),
                name: str

            }

        Parameters
        ----------
        submission_id: int
            ID of the corresponding job submission
        payload: dict
            description of the tool job
        '''
        if payload['task'] == 'classification':
            self.perform_classification(submission_id, payload)
        elif payload['task'] == 'save_labels':
            self.save_selections(submission_id, payload)
        else:
            raise ValueError('Tool {} is not implemented'.format(payload['task']))


    def perform_classification(self, submission_id, payload):
        '''Processes a client tool request and inserts the generated result
        into the database. This function deals with the classification jobs.
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
                },
                "task": str (either 'classification' or 'save_labels'),
                name: str

            }

        Parameters
        ----------
        submission_id: int
            ID of the corresponding job submission
        payload: dict
            description of the tool job
        '''
        logger.debug('perform supervised classification')
        mapobject_type_name = payload['chosen_object_type']
        feature_names = payload['selected_features']
        method = payload['options']['method']
        n_fold_cv = payload['options']['n_fold_cv']

        if method not in self.__options__['method']:
            raise ValueError('Unknown method "%s".' % method)

        labels = dict()
        label_map = dict()
        for cls_id, cls in enumerate(payload['training_classes']):
            labels.update({val: float(cls_id) for val in cls['object_ids']})
            label_map[float(cls_id)] = {'name': cls['name'],
                                        'color': cls['color']}

        unique_labels = np.unique(labels.values())

        # Build a name for the result, max. 30 characters in total. Cuts off
        # input names after character 20. (limited by database settings)
        result_name = payload['name'][:20] + '-' + str(submission_id)

        # Train the classifier
        result_id = self.register_result(
            submission_id, mapobject_type_name,
            result_type='SupervisedClassifierToolResult', name=result_name,
            unique_labels=unique_labels, label_map=label_map
        )

        training_set = self.load_feature_values(
            mapobject_type_name, feature_names, labels.keys()
        )
        logger.info('train classifier')
        model, scaler = self.train_supervised(
            training_set, labels, method, n_fold_cv
        )

        n_test = 10**5
        logger.debug('set batch size to %d', n_test)
        batches = self.partition_mapobjects(mapobject_type_name, n_test)
        for i, mapobject_ids in enumerate(batches):
            logger.info('predict labels for batch #%d', i)
            test_set = self.load_feature_values(
                mapobject_type_name, feature_names, mapobject_ids
            )
            predicted_labels = self.predict(test_set, model, scaler)
            self.save_result_values(
                mapobject_type_name, result_id, predicted_labels
            )

    def save_selections(self, submission_id, payload):
        '''Processes a client tool request and inserts the generated result
        into the database. This function deals with the save labels jobs.
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
                },
                "task": str (either 'classification' or 'save_labels'),
                name: str

            }

        Parameters
        ----------
        submission_id: int
            ID of the corresponding job submission
        payload: dict
            description of the tool job
        '''
        logger.debug('Saving current selections for submission id: '
                     + str(submission_id))
        mapobject_type_name = payload['chosen_object_type']

        labels = dict()
        label_map = dict()
        for cls_id, cls in enumerate(payload['training_classes']):
            labels.update({val: float(cls_id) for val in cls['object_ids']})
            label_map[float(cls_id)] = {'name': cls['name'],
                                        'color': cls['color']}

        unique_labels = np.unique(labels.values())

        # Create a MultiIndex pandas.Series for the input labels, because
        # the save_results_values expects such a pandas Series.
        # Keys are mapobject ids, values are the actual labels
        # Hard-coding tpoint = 0 is suboptimal, but I don't know how I
        # would get the actual tpoint information and as far as I can see, it
        # does not matter. It's just required to create the same kind of data
        # structure to be saved as in perform_classification.
        # To fix this, check how it's done in load_feature_values
        tpoint = 0
        indices = [(label, tpoint) for label in labels.keys()]

        index = pd.MultiIndex.from_tuples(
            indices, names=['mapobject_id', 'tpoint']
        )

        label_array = np.array(labels.values())
        label_series = pd.Series(label_array, index=index)

        # Build a name for the result, max. 30 characters in total. Cuts off
        # input names after character 20. (limited by database settings)
        label_name = payload['name'][:20] + '-Lbs-' + str(submission_id)

        label_result_id = self.register_result(
             submission_id, mapobject_type_name,
             result_type='SupervisedClassifierToolResult', name=label_name,
             unique_labels=unique_labels, label_map=label_map
        )

        self.save_result_values(
            mapobject_type_name, label_result_id, label_series
        )
