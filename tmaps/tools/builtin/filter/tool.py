from collections import defaultdict

import numpy as np

from tmaps.tools import register_tool, Tool


@register_tool('Filter')
class FilterTool(Tool):
    def process_request(self, payload):
        features = payload.get('features')
        data = self.experiment_dataset
        header = data['/cells/features'].attrs['names']
        mat = data['/cells/features'][()]

        masks_per_feat = []

        for f in feature_names:
            col = mat[:, header == f['name']]
            min_ = f['range'][0]
            max_ = f['range'][1]

            is_in_range = np.logical_and(min_ <= col, col <= max_)
            # This is a n x 1 matrix, convert
            # it to a normal vector of 1 dimension, i.e. shape: (n, )
            masks_per_feat.append(is_in_range[:, 0])

        if len(masks_per_feat) > 1:
            cell_in_ranges = np.logical_and(*masks_per_feat)
        else:
            cell_in_ranges = masks_per_feat[0]

        ncells = len(cell_in_ranges)

        lut = np.zeros((ncells, 3), np.uint8)
        lut[cell_in_ranges, :] = (255, 255, 255)

        self.client_proxy.add_layer_mod(
            'FIL (%d cells)' % np.sum(cell_in_ranges),
            source='area',
            funcname='modify_layer',
            modfunc_arg=lut.tolist(),
            render_args={
                'white_as_alpha': True
            }
        )

    @staticmethod
    def modify_layer(idmat, colors_lut):
        colors_lut = np.array(colors_lut)
        return colors_lut[idmat]
