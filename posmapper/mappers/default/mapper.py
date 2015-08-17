from scipy.misc import imread
from os.path import join
import os
import numpy as np
import re

from posmapper import register_position_mapper


_cached_site_sizes = {}


@register_position_mapper('default')
def get_cell_id_for_pos(experiment, posmapper_config, x, y):

    site_img_height, site_img_width = _get_site_size(experiment)

    # Map from global coordinates to site-local coordinates
    site_col = int(x / site_img_width)
    site_row = int(abs(y) / site_img_height)
    i = abs(y) % site_img_height
    j = x % site_img_width

    # Try to read the cell's id from a label matrix.
    # In the default format there is a label matrix for each site.
    segmentation_file_loc = _get_segmentation_file(
        experiment, site_row, site_col)
    segm_mat = np.load(segmentation_file_loc)
    cell_id = segm_mat[i, j]
    if cell_id == 0:
        return

    return int(cell_id)


def _get_segmentation_file(experiment, site_row, site_col):
    """Try to load the label matrix at a given site"""

    tabledir = join(experiment.location, 'id_tables')
    # coordinates in file names are one-based
    fname = r'ROW{row_nr:0>5}_COL{col_nr:0>5}.npy'.format(
        row_nr=site_row + 1, col_nr=site_col + 1)
    segmentation_file_loc = join(tabledir, fname)

    return segmentation_file_loc


def _get_site_size(experiment):
    if not experiment.name in _cached_site_sizes:
        segm_dir = join(experiment.location, 'posmapper')
        files = filter(lambda x: not x.startswith('.'), os.listdir(segm_dir))
        files = [join(segm_dir, f) for f in files]
        mat = imread(files[0])
        _cached_site_sizes[experiment.name] = mat.shape
    return _cached_site_sizes[experiment.name]
