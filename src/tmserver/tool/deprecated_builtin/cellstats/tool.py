import numpy as np

from tmserver.tool import register_tool, Tool


@register_tool('CellStats')
class CellStats(Tool):

    def process_request(self, payload):
        """
        Request:
        {
            "get_stats_for_cell_id": int
        }

        Response:
        {
            feature_values: [
                {
                    "feature": string,
                    "channel": string,
                    "value": number
                },
                ...
            ]
        }
        """

        all_ids = self.experiment_dataset['/cells/ids'][()]
        print payload
        cell_id = payload['get_stats_for_cell_id']
        row_idx = np.where(all_ids == cell_id)[0][0]

        featvals = []

        for ch in self.experiment_dataset['/channels']:
            dset = self.experiment_dataset['/channels'][ch]['features']
            featmat = dset[()]

            header = dset.attrs['names'].tolist()
            vals = featmat[row_idx, :].tolist()

            for featval, featname in zip(vals, header):
                featvals.append({
                    'feature': featname,
                    'channel': ch,
                    'value': featval
                })

        return {
            'feature_values':  featvals
        }
