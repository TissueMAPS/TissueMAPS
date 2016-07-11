import skimage.measure
import numpy as np
import mahotas as mh
from jtlib import utils

VERSION = '0.0.2'


def main(input_mask, feature, threshold, remove, plot):
    '''Filters objects (labeled connected components) based on specified
    features.

    Parameters
    ----------
    input_mask: numpy.ndarray[numpy.int32]
        labeled image that should be filtered
    feature: str
        name of the region property based on which the image should be filtered
        see `scikit-image docs <http://scikit-image.org/docs/dev/api/skimage.measure.html#regionprops>`_
    threshold:
        threshold level (type depends on the chosen `feature`)
    remove: str
        remove objects ``"below"`` or ``"above"`` `threshold`
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    Dict[str, numpy.ndarray[int32] or str]
        "filtered_image": filtered label image
        "figure": JSON string figure representation

    Raises
    ------
    ValueError
        when value of `remove` is not ``"below"`` or ``"above"``
    '''
    if input_mask.dtype != np.bool:
        raise TypeError('Argument label image must be binary')

    labeled_input_mask = mh.label(input_mask)[0]
    regions = skimage.measure.regionprops(labeled_input_mask)
    if remove == 'above':
        ids_to_keep = [r['label'] for r in regions if r[feature] < threshold]
    elif remove == 'below':
        ids_to_keep = [r['label'] for r in regions if r[feature] > threshold]
    else:
        raise ValueError(
            'Argument "remove" must be a either "above" or "below"'
        )

    filtered_image = np.zeros(input_mask.shape, dtype=input_mask.dtype)
    for ix in ids_to_keep:
        filtered_image[labeled_input_mask == ix] = ix

    n_removed = len(np.unique(labeled_input_mask)) - len(np.unique(filtered_image))

    output_mask = filtered_image > 0
    output = {'output_mask': output_mask}
    if plot:
        from jtlib import plotting
        plots = [
            plotting.create_mask_image_plot(input_mask, 'ul'),
            plotting.create_mask_image_plot(output_mask, 'ur'),
        ]
        output['figure'] = plotting.create_figure(
            plots,
            title='''removed %d objects with %s values %s %d
            ''' % (n_removed, feature, remove, threshold)
        )
    else:
        output['figure'] = str()

    return output
