from tmaps.tool import register_tool, Tool
import numpy as np


@register_tool('FeatureStats')
class FeatureStatsTool(Tool):

    def process_request(self, payload):

        feature = payload.get('feature')
        cells_per_selection = payload.get('selected_cells')

        if not feature or not cells_per_selection:
            raise Exception('Wrong arguments!')
        else:
            data = self._get_data(feature, cells_per_selection)
            return data

    def _get_data(self, feature, cells_per_selection):
        """
        Return value format:

        {
            'histogram_midpoints': list[float],
            'histograms': [
                {
                    'selection_name': string,
                    'values': list[float],
                    'histogram': list[float]
                },
                ...

            ]
        }

        """

        feature_name = feature['name']

        dset = self.experiment_dataset['/cellds/features']
        matrix = dset[()]

        feature_names = dset.attrs['names']
        feature_idx = np.nonzero(feature_names == feature_name)[0][0]

        feature_vector = matrix[:, feature_idx]

        response = {
            'histograms': []
        }

        hist_range = None
        for selection_name, cells in cells_per_selection.items():

            # Don't process the selection if it doesn't include any cells
            if not cells:
                continue

            idx = reduce(np.logical_or, [ids == id for id in cells])
            values = feature_vector[idx]

            if not hist_range:
                hist_range = (np.min(values), np.max(values))

            hist, bin_edges = np.histogram(
                values, range=hist_range, density=True)
            mid_points = (bin_edges[1:] + bin_edges[:-1]) / 2

            if not 'histogram_midpoints' in response:
                response['histogram_midpoints'] = mid_points.tolist()

            response['histograms'].append({
                'selection_name': selection_name,
                'values': values.tolist(),
                'histogram': hist.tolist()
            })

        return response
