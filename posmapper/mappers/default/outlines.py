from app import EXPDATA_DIR_LOCATION
from os.path import join
import h5py


# Where the precomputed outline files is
outline_file_location = join(
    EXPDATA_DIR_LOCATION, '{experiment_name}', 'outlines', 'outlines.hdf5')

_opened_outline_files = {}


def get_outline_for_pos(experiment_name, cell_id):
    try:
        outlines = _get_outline_file(experiment_name)
        coords = outlines[cell_id].value
        y = list(-1 * coords[:, 0])
        # Make negative since client needs negative y coords
        x = list(coords[:, 1])
        return (x, y)
    except KeyError:
        # Possibly a border cell
        raise


def _get_outline_file(expname):
    """Get the outline file for an experiment,
    cache it if it wasn't opened already"""
    if not expname in _opened_outline_files:
        file_loc = outline_file_location.format(experiment_name=expname)
        outlines = h5py.File(file_loc, 'r')
        _opened_outline_files[expname] = outlines
    return _opened_outline_files[expname]
