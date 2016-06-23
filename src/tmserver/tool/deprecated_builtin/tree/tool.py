import numpy as np
from sklearn import tree

from tmserver.tool import register_tool, Tool


@register_tool('DecisionTree')
class DecisionTreeTool(Tool):
    def process_request(self, payload):
        request_type = payload.get('request_type', None)

        self.client_proxy.log('Request received.')

        # Check if there is a request_type key in the received payload
        # so we know what to do with the received ata.
        if not request_type:
            msg = 'Tool DecisionTree needs a "request_type" key in its payload!'
            self.client_proxy.log(msg)
            raise Exception(msg)
        elif request_type == 'fit_model':
            features = payload.get('selected_features')
            cell_ids_per_class = payload.get('training_cell_ids')

            dataset = self.experiment_dataset

            self.client_proxy.log('Starting classification...')
            # Classification routine is in a sub function, call it now.
            predicted_labels = self._classify(
                dataset, features, cell_ids_per_class)

            # Now we can create a layermod that colors cells according to the
            # labels received by the classification step above.
            layermod_name = 'DTree: ' + '/'.join(
                [str(k) for k in cell_ids_per_class.keys()]
            )
            self.client_proxy.log('Done!')

            self.client_proxy.log('Sending layermod...')

            # The function `modify_layer` will modify the tiles of the
            # pyramid that encodes cell ids as RGB-tuples.
            # The predicted labels (which is actually a lookup table from cell
            # id to RGB) are passed to the function so it knows what
            # cell id should get what color.
            self.client_proxy.add_layer_mod(
                layermod_name,
                source='area',
                funcname='modify_layer',
                modfunc_arg=predicted_labels
            )
            self.client_proxy.log('Done!')

        else:
            raise Exception('Not a known request type: ' + request_type)

    def _classify(self, data, features, cell_ids_per_class):
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

        # Go through all features that should be used in training
        header = data['/objects/cells/features'].attrs['names']
        is_col_included = reduce(np.logical_or, [header == f for f in feature_names])

        cell_ids = data['/objects/cells/ids'][()]

        # Create a matrix with the columns that correspond to the features
        # in `feats`.
        mat = data['/objects/cells/features'][()]  # as numpy array

        ix = np.array(
            [np.where(cell_id == cell_ids)[0] for cell_id in training_cell_ids]
        )

        X_train = mat[ix, is_col_included]
        y_train = np.array(
            [class_per_cell_id[cell_id] for cell_id in training_cell_ids]
        )

        X_new = mat[:, is_col_included]

        clf = tree.DecisionTreeClassifier()

        # Perform the actual model fitting
        clf.fit(X_train, y_train)

        # Predict all cells using the new classifier
        y_pred = clf.predict(X_new)

        # We now create a color lookup table that maps global cell ids to
        # RGB-tuples. For this we create a tall (n x 3) matrix  whose row index
        # corresponds to the cell id and each column specifies whether the value
        # in the matrix cell is R, G or B. Note that we have to add one more row
        # since the index 0 corresponds to the background which should stay
        # black when we pipe the cell ids through this LUT.
        highest_cell_id = np.max(cell_ids)
        color_lut = np.zeros((highest_cell_id + 1, 3))

        for cell_id, predicted_classname in zip(cell_ids, y_pred):
            color_lut[cell_id, :] = classname_to_color[predicted_classname]

        # Return a python-list version of the color lookup table to
        # `process_request`, so that the LUT can be saved in a layermod.
        return color_lut.tolist()

    @staticmethod
    def modify_layer(idmat, colors_lut):
        colors_lut = np.array(colors_lut)
        return colors_lut[idmat]
