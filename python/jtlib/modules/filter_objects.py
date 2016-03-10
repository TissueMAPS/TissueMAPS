import skimage.measure
import numpy as np
from .. import utils


def filter_objects(label_image, feature, threshold, remove, relabel, plot):
    '''
    Jterator module to filter labeled image regions (objects) based
    on measured features.

    Parameters
    ----------
    label_image: numpy.ndarray[numpy.bool or numpy.int32]
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
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    Dict[str, numpy.ndarray[int32] or str]
        "filtered_objects": filtered label image
        "figure": html string in case ``kwargs["plot"] == True``

    Raises
    ------
    ValueError
        when value of `remove` is not ``"below"`` or ``"above"``
    '''
    is_binary = len(np.unique(label_image)) == 2
    if is_binary:
        # In case the input is a binary mask, we first have to label the
        # objects in order to be able to keep track of them.
        label_image = utils.label_image(label_image)
    regions = skimage.measure.regionprops(label_image)
    if remove == 'above':
        ids_to_keep = [r['label'] for r in regions if r[feature] < threshold]
    elif remove == 'below':
        ids_to_keep = [r['label'] for r in regions if r[feature] > threshold]
    else:
        raise ValueError('Value of argument `remove` must be a either '
                         '"above" or "below"')

    filtered_image = np.zeros(label_image.shape)
    for ix in ids_to_keep:
        filtered_image[label_image == ix] = ix

    n_removed = len(np.unique(label_image)) - len(np.unique(filtered_image))

    if is_binary:
        # Convert images back to binary mask.
        label_image = label_image > 0
        filtered_image = filtered_image > 0

    if relabel:
        filtered_image = utils.label_image(filtered_image > 0)

    output = {'filtered_objects': filtered_image}
    if plot:
        from .. import plotting

        plots = [
            plotting.create_mask_image_plot(label_image, 'ul'),
            plotting.create_mask_image_plot(filtered_image, 'ur'),
        ]

        output['figure'] = plotting.create_figure(
                                plots, title='''
                                    removed %d objects with %s values %s %d
                                ''' % (n_removed, feature, remove, threshold)
        )

    return output
