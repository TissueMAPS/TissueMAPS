'''Jterator module for creation of object clipping masks.'''
import numpy as np

VERSION = '0.0.1'

def main(outer_mask, inner_mask, plot=False):
    '''Clips a labeled or binary mask, such that the intersecting pixels/voxels
    are set to background.

    Parameters
    ----------
    outer_mask: numpy.ndarray[numpy.int32]
        mask that should be clipped
    inner_mask: numpy.ndarray[numpy.int32]
        intersecting mask that should be used for clipping
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    Dict[str, numpy.ndarray[numpy.int32] or str]
        * "clipped_mask": clipped mask
        * "figure": JSON string representation of the figure
    '''
    clipped_mask = np.copy(outer_mask)
    clipped_mask
    clipped_mask[inner_mask > 0] = 0
    outputs = dict()
    outputs['clipped_mask'] = clipped_mask
    outputs['figure'] = str()
    if plot:
        outputs['figure'] = str()
    return outputs
