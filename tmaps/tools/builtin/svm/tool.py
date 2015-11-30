from collections import defaultdict
from tmaps.tools import register_tool, Tool

from sklearn import svm
import numpy as np
import pandas as pd
from matplotlib import cm

from tmlib.readers import DatasetReader


@register_tool('SVM')
class SVMTool(Tool):
    def process_request(self, payload, experiment):
        """
        {
            request_type: str,
            selected_features: [
                {
                    name: str
                },
                ...
            ],
            training_cell_ids: {
                CLASS_1_LABEL: {
                    color: [255, 0, 0, 1],
                    cells: [int, int, int, ...]
                },
                ...
            }
        }

        """
        # import ipdb; ipdb.set_trace()
        # message = payload.get('message', 'no message given')
        # request_type = payload['request_type']
        # selected_feature_names = \
            # [f['name'] for f in payload['selected_features']]
        # return {
        #     'classes': [
        #         {
        #             'label': 'class1',
        #             'color': {'r': 255, 'g': 0, 'b': 0},
        #             'cell_ids': map(str, range(0, 200))
        #         },
        #         {
        #             'label': 'class2',
        #             'color': {'r': 0, 'g': 255, 'b': 0},
        #             'cell_ids': map(str, range(400, 600))
        #         },
        #         {
        #             'label': 'class3',
        #             'color': {'r': 0, 'g': 0, 'b': 255},
        #             'cell_ids': map(str, range(800, 1000))
        #         }
        #     ]
        # }

        features = payload.get('selected_features')
        cell_ids_per_class = payload.get('training_cell_ids')

        dataset = pd.DataFrame()
        with DatasetReader(experiment.dataset_path) as data:
            group = '/objects/cells/features'
            datasets = data.list_datasets(group)
            for d in datasets:
                dataset[d] = data.read('%s/%s' % (group, d))

        # Classification routine is in a sub function, call it now.
        predicted_labels = self._classify_dtree(
            dataset, features, cell_ids_per_class)

        available_colors = [
            {'r': 255, 'g': 0, 'b': 0},
            {'r': 0, 'g': 255, 'b': 0},
            {'r': 0, 'g': 0, 'b': 255},
            {'r': 255, 'g': 0, 'b': 255},
            {'r': 20, 'g': 50, 'b': 255}
        ]

        cls_labels = cell_ids_per_class.keys()
        colors = dict(zip(cls_labels, available_colors[:len(cls_labels)]))

        return {
            'cell_ids': dataset.index.tolist(),
            'predicted_labels': predicted_labels.tolist(),
            'colors': colors
        }

    def _classify(self, data, features, cell_ids_per_class):
        # Extract the class names that were sent from the client
        classname_to_color = {}

        # Simplify the received dictionary and extract requested label colors.
        # cell_ids_per_class should have the structure: string => list[int]
        for classname, classobj in cell_ids_per_class.items():
            cell_ids = map(int, classobj['cells'])
            cell_ids_per_class[classname] = cell_ids
            classname_to_color[classname] = classobj['color']

        feature_names = [f['name'] for f in features]

        # Create a map cell id to class name
        class_per_cell_id = {}
        for cls, ids in cell_ids_per_class.items():
            for id in ids:
                class_per_cell_id[id] = cls

        ## Build training data set

        # Construct design matrix from features that were selected on a
        # per-channel basis and from the selected cells.

        training_cell_ids = np.array(sum(cell_ids_per_class.values(), []))
        training_cell_ids_zb = training_cell_ids - 1  # zero based

        # Go through all features that should be used in training
        header = data['/objects/cells/features'].attrs['names']
        is_col_included = reduce(np.logical_or, [header == f for f in feature_names])

        cell_ids = data['/objects/cells/ids'][()]

        # Create a matrix with the columns that correspond to the features
        # in `feats`.
        mat = data['/objects/cells/features'][()]  # as numpy array
        X_train = mat[training_cell_ids_zb, :][:, is_col_included]
        X_new = mat[:, is_col_included]

        # A vector of class labels for the cells that should be used in training
        y_train = np.array(map(lambda id: class_per_cell_id[id], training_cell_ids))

        # TODO: Allow specification of other kernels.
        # TODO: Does the SVC routine automatically tune its hyper parameters or
        # do we have to perform a gridsearch for the optimal lambda?
        cls = svm.SVC(kernel='rbf')

        # Perform the actual model fitting
        cls.fit(X_train, y_train)

        # Predict all cells using the new classifier
        y_pred = cls.predict(X_new)

        return y_pred


    def _classify_dtree(self, data, features, cell_ids_per_class):
        from sklearn import tree
        # Extract the class names that were sent from the client
        classname_to_color = {}

        # Simplify the received dictionary and extract requested label colors.
        # cell_ids_per_class should have the structure: string => list[int]
        class_idx = 0
        for classname, classobj in cell_ids_per_class.items():
            cell_ids = map(int, classobj['cells'])
            cell_ids_per_class[class_idx] = cell_ids
            del cell_ids_per_class[classname]
            classname_to_color[class_idx] = classobj['color']
            class_idx += 1

        feature_names = [f['name'] for f in features]

        # Create a map cell id to class name
        class_per_cell_id = {}
        for cls, ids in cell_ids_per_class.items():
            for id in ids:
                class_per_cell_id[id] = cls

        ## Build training data set

        # Construct design matrix from features that were selected on a
        # per-channel basis and from the selected cells.

        training_cell_ids = np.array(sum(cell_ids_per_class.values(), []))

        cell_ids = cell_ids = data.index.tolist()

        # Create a matrix with the columns that correspond to the features
        # in `feats`.
        ix = np.array(
            [np.where(cell_id == cell_ids)[0] for cell_id in training_cell_ids]
        )

        X_train = data.loc[ix, feature_names]
        y_train = np.array(
            [class_per_cell_id[cell_id] for cell_id in training_cell_ids]
        )

        X_new = data.loc[:, feature_names]

        clf = tree.DecisionTreeClassifier()

        # Perform the actual model fitting
        clf.fit(X_train, y_train)

        # Predict all cells using the new classifier
        y_pred = clf.predict(X_new)

        return y_pred
