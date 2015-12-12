from collections import defaultdict
from tmaps.tools import register_tool, Tool

from sklearn import svm
import numpy as np
from matplotlib import cm


@register_tool('SVM')
class SVMTool(Tool):
    def process_request(self, payload, experiment):
        """
        {
            "chosen_object_type": str,
            "selected_features": List[str],
            "training_classes": List[
                {
                    "name": str,
                    "object_ids": List[int],
                    "color": {r: int, g: int, b: int, a: float}
                }
            ]
        }
        

        """
        # import ipdb; ipdb.set_trace()
        # message = payload.get('message', 'no message given')
        # request_type = payload['request_type']
        # selected_feature_names = \
            # [f['name'] for f in payload['selected_features']]
        # return {
        #     'object_type': 'nuclei',
        #     'predicted_labels': ['A'] * 100 + ['B'] * 100,
        #     'colors': {
        #         'A': {'r': 255, 'g': 0, 'b': 0},
        #         'B': {'r': 0, 'g': 0, 'b': 255}
        #     },
        #     'object_ids': range(200)
        # }

        features = payload['selected_features']
        object_ids_per_class = \
            {cls['name']: cls['object_ids'] for cls in payload['training_classes']}
        object_type = payload['chosen_object_type']
        class_color_map = \
            {cls['name']: cls['color'] for cls in payload['training_classes']}

        # Classification routine is in a sub function, call it now.
        with experiment.dataset as dataset:
            ids = dataset['/objects/%s/ids' % object_type][:]
            predicted_labels = self._classify_dtree(
                dataset, object_type, features, object_ids_per_class)

        return {
            'object_type': object_type,
            'object_ids': ids.tolist(),
            'predicted_labels': predicted_labels.tolist(),
            'colors': class_color_map
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


    def _classify_dtree(self, data, object_type, feature_names, object_ids_per_class):
        """Classify map objects of a given type based on a set of selected features
        using specific objects training data and a decision tree classifier.
        
        Parameters
        ----------
        data : h5py dataset
            The experiments dataset.
        object_type : str
            The object type as a string. This will be used to index into the dataset.
        feature_names : List[str]
            A list of feature names to use for training and classifying.
        object_ids_per_class : Dict[str, List[int]]
            A dictionary holding the training data. It maps class labels to
            the object ids that should be used as the training examples for that
            class. 
        
        Returns
        -------
        np.array
            An array of predicted class labels for all objects of the chosen type.
        
        """
        from sklearn import tree
        # Create a map cell id to class name
        class_per_object_id = {}
        for cls, ids in object_ids_per_class.items():
            for id in ids:
                class_per_object_id[id] = cls

        ### Build training data set
        # Construct design matrix from features and objects that were selected.
        training_cell_ids = np.array(class_per_object_id.keys())

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

        X_train = X[training_cell_ids, :]
        y_train = np.array(
            [class_per_object_id[cell_id] for cell_id in training_cell_ids]
        )

        # Predict all objects
        X_new = X

        ### Perform the actual model fitting
        clf = tree.DecisionTreeClassifier()
        clf.fit(X_train, y_train)

        ### Predict all cells using the new classifier
        y_pred = clf.predict(X_new)

        return y_pred
