'''Jterator module for creation of object clipping masks.'''
import numpy as np
import collections

VERSION = '0.0.1'

Output = collections.namedtuple('Output', ['clipped_mask', 'figure'])


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
    jtmodules.clip_objects.Output
    '''
    clipped_mask = np.copy(outer_mask)
    clipped_mask
    clipped_mask[inner_mask > 0] = 0
    clipped_mask = clipped_mask

    if plot:
        # TODO
        figure = str()
    else:
        figure = str()

    return Output(clipped_mask, figure)
