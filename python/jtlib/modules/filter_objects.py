import skimage.measure
import collections
import numpy as np
from .. import utils


def filter_objects(labeled_image, feature, threshold, keep, relabel, **kwargs):
    '''
    Jterator module to filter labeled image regions (objects) based
    on measured features.

    Parameters
    ----------
    labeled_image: numpy.ndarray[int]
        labeled image that should be filtered
    feature: str
        name of the region property based on which the image should be filtered
        see `scikit-image docs <http://scikit-image.org/docs/dev/api/skimage.measure.html#regionprops>`_
    threshold:
        threshold level (type depends on the chosen `feature`)
    keep: str
        ``"below"`` or ``"above"``
    relabel: bool
        relabel objects after filtering
    **kwargs: dict
        additional arguments provided by Jterator:
        "data_file", "figure_file", "experiment_dir", "plot", "job_id"

    Returns
    -------
    collections.namedtuple[numpy.ndarray[bool]]
        filtered label image: "filtered_objects"

    Raises
    ------
    ValueError
        when value of `keep` is incorrect
    '''
    regions = skimage.measure.regionprops(labeled_image)
    if keep == 'above':
        ids_to_keep = [r['label'] for r in regions if r[feature] > threshold]
    elif keep == 'below':
        ids_to_keep = [r['label'] for r in regions if r[feature] < threshold]
    else:
        raise ValueError('Value of argument `keep` must be a either '
                         '"above" or "below"')

    filtered_image = np.zeros(labeled_image.shape)
    for ix in ids_to_keep:
        filtered_image[labeled_image == ix] = ix

    if relabel:
        filtered_image = utils.label_image(filtered_image > 0)

    if kwargs['plot']:
        import plotly
        from .. import plotting

        rf = 4
        ds_labl_img = skimage.measure.block_reduce(
                            labeled_image, (rf, rf), func=np.mean).astype(int)
        ds_filt_img = skimage.measure.block_reduce(
                            filtered_image, (rf, rf), func=np.mean).astype(int)

        n_labeled = len(np.unique(ds_labl_img[ds_labl_img > 0]))
        n_filtered = len(np.unique(ds_filt_img[ds_filt_img > 0]))

        if n_labeled == 1:
            colors = [[0, 'rgb(0,0,0)'], [1, plotting.OBJECT_COLOR]]
        else:
            colors = plotting.create_plotly_palette('Set1', n_labeled)

        data = [
            plotly.graph_objs.Heatmap(
                z=ds_labl_img,
                hoverinfo='z',
                colorscale=colors,
                # colorbar=dict(yanchor='bottom', y=0.55, len=0.45),
                showscale=False,
                y=np.linspace(0, labeled_image.shape[0], ds_labl_img.shape[0]),
                x=np.linspace(0, labeled_image.shape[1], ds_labl_img.shape[1])
            ),
            plotly.graph_objs.Heatmap(
                z=ds_filt_img,
                hoverinfo='z',
                colorscale=colors[:n_filtered+1],
                showscale=False,
                y=np.linspace(0, filtered_image.shape[0], ds_filt_img.shape[0]),
                x=np.linspace(0, filtered_image.shape[1], ds_filt_img.shape[1]),
                xaxis='x2',
                yaxis='y2'
            )
        ]

        layout = plotly.graph_objs.Layout(
            title='Objects with {feature} values {above_below} {level}'.format(
                        feature=feature, above_below=keep, level=threshold),
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

    Output = collections.namedtuple('Output', 'filtered_objects')
    return Output(filtered_image)
