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

    __description__ = '''
        Clusters mapobjects based on a set of selected features.
    '''

    __methods__ = ['kmeans']

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

        feature_data = self.load_feature_values(
            mapobject_type_name, feature_names
        )
        predicted_labels = self.classify_unsupervised(feature_data, k, method)

        unique_labels = self.calculate_unique(predicted_labels, 'label')
        result_id = self.initialize_result(
            submission_id, mapobject_type_name,
            layer_type='ScalarLabelLayer', unique_labels=unique_labels
        )

        self.save_label_values(result_id, predicted_labels)
