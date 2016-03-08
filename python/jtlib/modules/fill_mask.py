from scipy import ndimage as ndi
import collections


def fill_mask(mask, **kwargs):
    '''
    Jterator module to fill holes (enclosed pixel regions of connected components)
    in a binary image.

    Parameters
    ----------
    mask: numpy.ndarray
        binary image that should be filled
    **kwargs: dict
        additional arguments provided by Jterator:
        "data_file", "figure_file", "experiment_dir", "plot", "job_id"

    Returns
    -------
    collections.namedtuple[numpy.ndarray[bool]]
        filled binary image: "filled_mask"
    '''
    filled_mask = ndi.binary_fill_holes(mask)

    if kwargs['plot']:
        import plotly
        from .. import plotting

        plots = [
            plotting.create_mask_image_plot(mask, 'ul'),
            plotting.create_mask_image_plot(filled_mask, 'ur'),
        ]

        fig = plotting.create_figure(plots, title='Holes in mask filled.')
        plotting.save_figure(fig, kwargs['figure_file'])

    Output = collections.namedtuple('Output', 'filled_mask')
    return Output(filled_mask)
