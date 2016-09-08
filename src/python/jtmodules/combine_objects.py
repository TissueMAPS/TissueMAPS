'''Jterator module for combining objects from two binary mask images into one.
'''
import numpy as np


def main(input_mask_1, input_mask_2, plot=False):
    '''Combines two binary masks, such that the resulting combined mask
    is ``True`` where either `input_mask_1` OR `input_mask_2` is ``True``.

    Parameters
    ----------
    input_mask_1: numpy.ndarray[numpy.bool]
        2D binary array
    input_mask_2: numpy.ndarray[numpy.bool]
        2D binary array

    Returns
    -------
    Dict[str, numpy.ndarray[numpy.bool] or str]
        * "output_mask": combined mask image
        * "figure": JSON figure representation

    '''
    combined_mask = np.logical_or(input_mask_1, input_mask_2)

    output = dict()
    output['output_mask'] = combined_mask
    if plot:
        from jtlib import plotting
        plots = [
            plotting.create_mask_image_plot(input_mask_1, 'ul'),
            plotting.create_mask_image_plot(input_mask_2, 'ur'),
            plotting.create_mask_image_plot(combined_mask, 'll')
        ]
        output['figure'] = plotting.create_figure(
            plots, title='combined mask'
        )
    else:
        output['figure'] = str()

    return output

