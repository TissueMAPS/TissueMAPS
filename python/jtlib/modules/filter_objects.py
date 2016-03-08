import skimage.measure
import collections
import numpy as np
from .. import utils


def filter_objects(labeled_image, feature, threshold, remove, relabel, **kwargs):
    '''
    Jterator module to filter labeled image regions (objects) based
    on measured features.

    Parameters
    ----------
    labeled_image: numpy.ndarray[numpy.bool or numpy.int32]
        labeled image that should be filtered
    feature: str
        name of the region property based on which the image should be filtered
        see `scikit-image docs <http://scikit-image.org/docs/dev/api/skimage.measure.html#regionprops>`_
    threshold:
        threshold level (type depends on the chosen `feature`)
    remove: str
        remove objects ``"below"`` or ``"above"`` `threshold`
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
    is_binary = len(np.unique(labeled_image)) == 2
    if is_binary:
        # In case the input is a binary mask, we first have to label the
        # objects in order to be able to keep track of them.
        labeled_image = utils.label_image(labeled_image)
    regions = skimage.measure.regionprops(labeled_image)
    if remove == 'above':
        ids_to_keep = [r['label'] for r in regions if r[feature] < threshold]
    elif remove == 'below':
        ids_to_keep = [r['label'] for r in regions if r[feature] > threshold]
    else:
        raise ValueError('Value of argument `remove` must be a either '
                         '"above" or "below"')

    filtered_image = np.zeros(labeled_image.shape)
    for ix in ids_to_keep:
        filtered_image[labeled_image == ix] = ix

    n_removed = len(np.unique(labeled_image)) - len(np.unique(filtered_image))

    if is_binary:
        # Convert images back to binary mask.
        labeled_image = labeled_image > 0
        filtered_image = filtered_image > 0

    if relabel:
        filtered_image = utils.label_image(filtered_image > 0)

    if kwargs['plot']:
        from .. import plotting

        plots = [
            plotting.create_mask_image_plot(labeled_image, 'ul'),
            plotting.create_mask_image_plot(filtered_image, 'ur'),
        ]

        fig = plotting.create_figure(
                    plots, title='''
                        removed %d objects with %s values %s %d
                    ''' % (n_removed, feature, remove, threshold)
        )
        plotting.save_figure(fig, kwargs['figure_file'])

    Output = collections.namedtuple('Output', 'filtered_objects')
    return Output(filtered_image)
