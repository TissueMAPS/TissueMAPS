from scipy import ndimage as ndi
import collections
import numpy as np
import skimage


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

        rf = 4
        ds_mask = skimage.measure.block_reduce(
                            mask, (rf, rf), func=np.mean).astype(int)
        ds_filled_mask = skimage.measure.block_reduce(
                            filled_mask, (rf, rf), func=np.mean).astype(int)

        colors = [[0, 'rgb(0,0,0)'], [1, plotting.OBJECT_COLOR]]

        data = [
            plotly.graph_objs.Heatmap(
                z=ds_mask,
                colorscale=colors,
                hoverinfo='z',
                zmin=0,
                showscale=False,
                y=np.linspace(0, mask.shape[0], ds_mask.shape[0]),
                x=np.linspace(0, mask.shape[1], ds_mask.shape[1])
            ),
            plotly.graph_objs.Heatmap(
                z=ds_filled_mask,
                colorscale=colors,
                hoverinfo='z',
                showscale=False,
                y=np.linspace(0, mask.shape[0], ds_mask.shape[0]),
                x=np.linspace(0, mask.shape[1], ds_mask.shape[1]),
                xaxis='x2',
                yaxis='y2'
            )
        ]

        layout = plotly.graph_objs.Layout(
            title='Filled mask',
            xaxis1=dict(
                domain=[0, 0.43],
                anchor='y1'
            ),
            yaxis1=dict(
                domain=[0.57, 1],
                anchor='x1',
                autorange='reversed'
            ),
            xaxis2=dict(
                domain=[0.57, 1],
                anchor='y2'
            ),
            yaxis2=dict(
                ticks='', showticklabels=False,
                domain=[0.57, 1],
                anchor='x2',
                autorange='reversed'
            ),
        )

        fig = plotly.graph_objs.Figure(data=data, layout=layout)
        plotting.save_plotly_figure(fig, kwargs['figure_file'])

    Output = collections.namedtuple('Output', 'filled_mask')
    return Output(filled_mask)
