from scipy import ndimage as ndi

VERSION = '0.0.1'

def main(mask, plot=False):
    '''Fills holes (enclosed pixel regions of connected components)
    in a binary image.

    Parameters
    ----------
    mask: numpy.ndarray[numpy.bool]
        binary image that should be filled
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    Dict[str, numpy.ndarray[numpy.int32] or str]
        "filled_mask": filled binary image
        "figure": html string in case `plot` is ``True``
    '''
    filled_mask = ndi.binary_fill_holes(mask)

    output = {'filled_mask': filled_mask}
    if plot:
        from jtlib import plotting

        plots = [
            plotting.create_mask_image_plot(mask, 'ul'),
            plotting.create_mask_image_plot(filled_mask, 'ur'),
        ]

        output['figure'] = plotting.create_figure(
                                plots, title='Holes in mask filled.')
    else:
        output['figure'] = str()

    return output
