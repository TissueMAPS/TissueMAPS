from collections import defaultdict

from tools import register_tool, Tool
from scipy.cluster.vq import kmeans, vq
import numpy as np
from matplotlib import cm

import numpy as np

@register_tool('Cluster')
class ClusterTool(Tool):
    def process_request(self, payload):
        """
        Process a request sent by the client-side representation of ClusterTool.
        A request may look as follows:

        - Perform the clustering and respond with a layer mod

            Request:
            {
                "request_type": "perform_clustering",
                "features": [
                    {
                        "name": string
                    }
                    ...
                ],
                "k": integer (number of clusters to find with kmeans)
            }

        """
        request_type = payload.get('request_type', None)

        if not request_type:
            raise Exception('Tool "Cluster" needs a "request_type"'
                            ' key in its payload!')
        elif request_type == 'perform_clustering':

            features = payload['features']
            k = payload['k']

            clusterlabels = self._perform_clustering(
                self.experiment_dataset, features, k)

            self.client_proxy.add_layer_mod(
                'CLU',
                source='area',
                funcname='modify_layer',
                modfunc_arg=clusterlabels
            )

        else:
            raise Exception('Not a known request type: ' + request_type)

    def _perform_clustering(self, dataset, features, k):
        feature_names = [f['name'] for f in features]

        # available feature names for channel `channel`
        h5_location = '/objects/cells/features'
        cell_ids = dataset['/objects/cells/ids'][()]

        header = dataset[h5_location].attrs['names']
        is_col_included = reduce(np.logical_or, [header == f for f in feature_names])

        # Feature dataset as numpy array
        mat = dataset[h5_location][()]

        # Extract a submatrix that only contains the features wich should be
        # used to perform the clustering
        X = mat[:, is_col_included]

        # Compute the cluster centroids
        # centroids is a (k, p) where each row is a centroid in the
        # p-dimensional feature space
        centroids, _ = kmeans(X, k)
        # Assign each example/obs to its nearest centroid
        # and return a vector of length N indicating the cluster to which
        # each observation is to be assigned (as an integer).
        clusterlabels, _ = vq(X, centroids)

        # import ipdb; ipdb.set_trace()

        # A vector of ids. Each id has the format '{rownr}-{colnr}-{localid}'
        # ids = dataset['ids'][()]

        # import ipdb; ipdb.set_trace()
        # Expand range of labels s.t. resulting colors will be more dissimilar
        clusterlabels = clusterlabels * 256 / k
        colors_walpha = cm.jet(clusterlabels) * 256
        # Delete last column (corresponds to alpha values)
        colors = np.delete(colors_walpha, 3, axis=1)
        colors = colors.astype('uint8') # convert from float to uchar
        # Add black in front so that cell id 0 (which is the background) gets black
        # NOTE: This LUT assumed that all cell ids go from 1 to nrow(dataset)


        highest_cell_id = np.max(cell_ids)
        for x in range(100):
            print highest_cell_id
        color_lut = np.zeros((highest_cell_id + 1, 3))
        color_lut[cell_ids, :] = colors
        # color_lut = np.vstack([(0, 0, 0), colors])

        # is_larger = X.reshape(-1) > np.median(X)
        # color_lut[is_larger, :] = (200, 50, 20)
        # color_lut[np.logical_not(is_larger), :] = (0, 0, 255)
        return color_lut.tolist()

    @staticmethod
    def modify_layer(idmat, colors_lut):
        colors_lut = np.array(colors_lut)
        return colors_lut[idmat]
